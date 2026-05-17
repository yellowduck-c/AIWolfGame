import { storeToRefs } from 'pinia'

import { useGameStore } from '../stores/game_store'

export const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'
export const wsBaseUrl = import.meta.env.VITE_WS_BASE_URL ?? 'ws://127.0.0.1:8000/ws'

type BackendEvent =
  | { event: 'GAME_STARTED'; game_id: string; agents: Array<{ id: number; role: string; camp: string; status: 'alive' | 'dead' | 'exiled' }> }
  | { event: 'GAME_PAUSED'; game_id: string; status: string; phase: string }
  | { event: 'GAME_OVER'; game_id?: string; winner: string }
  | { event: 'GAME_RESET'; message?: string }
  | { event: 'AGENT_SPEAK_CHUNK'; id: number; role: string; content: string }
  | { event: 'AGENT_SPEAK'; id: number; role: string; content: string }
  | {
      event: 'AGENT_STATUS_CHANGE'
      id: number
      status: 'alive' | 'dead' | 'exiled'
      role?: string
      revealed_role?: string
      can_vote?: boolean
      can_speak?: boolean
      is_alive?: boolean
      special?: string
    }
  | { event: 'AGENT_VOTE'; id: number; target_id: number }
  | { event: 'AGENT_SKILL'; id: number; role: string; skill: string; target_id: number | null }
  | { event: 'PHASE_CHANGE'; phase: string; round?: number }
  | { event: 'CONNECTED'; message: string }
  | { event: 'ECHO'; payload: string }
  | { event: 'ERROR'; message: string }

let socket: WebSocket | null = null

function handleEvent(event: BackendEvent): void {
  const gameStore = useGameStore()

  switch (event.event) {
    case 'GAME_STARTED':
      gameStore.setCurrentGameId(event.game_id)
      gameStore.initializeAgents(event.agents)
      gameStore.setConnectionStatus('connected', `对局已启动：${event.game_id}`)
      break
    case 'GAME_PAUSED':
      gameStore.clearPendingCommand()
      gameStore.setPhase(event.phase)
      gameStore.setConnectionStatus('connected', `对局已暂停：${event.game_id}`)
      break
    case 'AGENT_SPEAK_CHUNK':
      gameStore.updateStreamingSpeech(event)
      break
    case 'AGENT_SPEAK':
      gameStore.appendSpeech(event)
      break
    case 'AGENT_STATUS_CHANGE':
      gameStore.updateAgentStatus(event)
      if (event.status === 'exiled' && event.revealed_role === '白痴') {
        gameStore.appendSystemLog({
          id: event.id,
          role: '系统',
          content: `${event.id} 号玩家被投票放逐，身份公开为白痴，后续不可发言、不可投票。`,
        })
      }
      break
    case 'AGENT_VOTE':
      gameStore.appendSystemLog({
        id: event.id,
        role: '系统',
        content: `${event.id} 号玩家投票给 ${event.target_id} 号玩家。`,
      })
      break
    case 'AGENT_SKILL': {
      const targetText = event.target_id === null ? '无目标' : `${event.target_id} 号玩家`
      gameStore.appendSystemLog({
        id: event.id,
        role: event.role,
        content: `${event.id} 号玩家发动技能 ${event.skill}，目标：${targetText}。`,
      })
      break
    }
    case 'PHASE_CHANGE':
      gameStore.setPhase(event.phase)
      break
    case 'GAME_OVER':
      gameStore.setPhase('finished')
      gameStore.clearPendingCommand()
      gameStore.setLiveGameStarted(false)
      gameStore.setWinner(event.winner)
      if (event.game_id) {
        gameStore.setCurrentGameId(event.game_id)
      }
      gameStore.setConnectionStatus('connected', `对局结束，胜者：${event.winner}`)
      break
    case 'GAME_RESET':
      gameStore.resetGameState()
      gameStore.setConnectionStatus('connected', event.message ?? '对局已重置，可重新开始。')
      break
    case 'CONNECTED':
      gameStore.clearPendingCommand()
      gameStore.setConnectionStatus('connected', event.message)
      break
    case 'ECHO': {
      const message = `后端已收到指令：${event.payload}`
      if (event.payload.includes('GAME_START')) {
        gameStore.setConnectionStatus('connected', `${message}，等待对局启动事件...`)
      } else {
        gameStore.setConnectionStatus('connected', message)
      }
      break
    }
    case 'ERROR':
      gameStore.clearPendingCommand()
      gameStore.setConnectionStatus('error', event.message)
      break
    default:
      gameStore.setConnectionStatus('error', `收到未适配事件：${JSON.stringify(event)}`)
      break
  }
}

export function connectGameWebSocket(): WebSocket | null {
  const gameStore = useGameStore()
  const { connectionStatus } = storeToRefs(gameStore)

  if (socket && (connectionStatus.value === 'connected' || connectionStatus.value === 'connecting')) {
    return socket
  }

  gameStore.setConnectionStatus('connecting', '正在建立 WebSocket 连接...')
  socket = new WebSocket(wsBaseUrl)

  socket.addEventListener('open', () => {
    gameStore.setConnectionStatus('connected', 'WebSocket 已连接，等待对局事件。')
  })

  socket.addEventListener('message', (messageEvent) => {
    try {
      const payload = JSON.parse(messageEvent.data) as BackendEvent
      handleEvent(payload)
    } catch {
      gameStore.setConnectionStatus('error', '收到无法解析的 WebSocket 消息。')
    }
  })

  socket.addEventListener('close', () => {
    gameStore.setConnectionStatus('disconnected', 'WebSocket 已断开。')
    socket = null
  })

  socket.addEventListener('error', () => {
    gameStore.setConnectionStatus('error', 'WebSocket 连接失败。')
  })

  return socket
}

type GameStartPayload = {
  cmd: 'GAME_START'
  player_count: number
  role_counts: Record<'werewolf' | 'seer' | 'witch' | 'hunter' | 'idiot' | 'villager', number>
  assigned_roles: Array<{ id: number; role_key: 'werewolf' | 'seer' | 'witch' | 'hunter' | 'idiot' | 'villager' }>
}

type GameControlPayload =
  | GameStartPayload
  | { cmd: 'GAME_PAUSE' | 'GAME_STOP' | 'GAME_RESET'; game_id?: string }

export function sendGameCommand(command: 'GAME_START' | 'GAME_PAUSE' | 'GAME_STOP' | 'GAME_RESET'): void {
  const gameStore = useGameStore()
  gameStore.setLastCommand(command)

  if (!socket || socket.readyState !== WebSocket.OPEN) {
    gameStore.clearPendingCommand()
    gameStore.setConnectionStatus('error', 'WebSocket 尚未连接，无法发送控制指令。')
    return
  }

  let payload: GameControlPayload
  if (command === 'GAME_START') {
    payload = { cmd: 'GAME_START', ...gameStore.buildGameStartConfig() }
  } else if (command === 'GAME_RESET') {
    payload = gameStore.currentGameId ? { cmd: 'GAME_RESET', game_id: gameStore.currentGameId } : { cmd: 'GAME_RESET' }
  } else {
    if (!gameStore.currentGameId) {
      gameStore.clearPendingCommand()
      gameStore.setConnectionStatus('error', `${command} 需要先启动对局并获取 game_id。`)
      return
    }
    payload = { cmd: command, game_id: gameStore.currentGameId }
  }

  gameStore.setPendingCommand(command)
  if (command === 'GAME_START') {
    gameStore.setLiveGameStarted(false)
    gameStore.setConnectionStatus('connected', '开始指令已发送，等待对局启动事件...')
  } else {
    gameStore.setConnectionStatus('connected', `${command} 指令已发送，等待后端响应...`)
  }
  socket.send(JSON.stringify(payload))
}
