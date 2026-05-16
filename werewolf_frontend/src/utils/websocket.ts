import { storeToRefs } from 'pinia'

import { useGameStore } from '../stores/game_store'

export const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'
export const wsBaseUrl = import.meta.env.VITE_WS_BASE_URL ?? 'ws://127.0.0.1:8000/ws'

type BackendEvent =
  | { event: 'GAME_STARTED'; agents: Array<{ id: number; role: string; camp: string; status: 'alive' | 'dead' | 'exiled' }> }
  | { event: 'AGENT_SPEAK'; id: number; role: string; content: string }
  | { event: 'AGENT_STATUS_CHANGE'; id: number; status: 'alive' | 'dead' | 'exiled' }
  | { event: 'PHASE_CHANGE'; phase: string }
  | { event: 'GAME_OVER'; winner: string }
  | { event: 'CONNECTED'; message: string }
  | { event: 'ECHO'; payload: string }

let socket: WebSocket | null = null

function handleEvent(event: BackendEvent): void {
  const gameStore = useGameStore()

  switch (event.event) {
    case 'GAME_STARTED':
      gameStore.initializeAgents(event.agents)
      gameStore.setPhase('night')
      break
    case 'AGENT_SPEAK':
      gameStore.appendSpeech(event)
      break
    case 'AGENT_STATUS_CHANGE':
      gameStore.updateAgentStatus(event)
      break
    case 'PHASE_CHANGE':
      gameStore.setPhase(event.phase)
      break
    case 'GAME_OVER':
      gameStore.setWinner(event.winner)
      break
    case 'CONNECTED':
      gameStore.setConnectionStatus('connected', event.message)
      break
    case 'ECHO':
      gameStore.setConnectionStatus('connected', `后端已收到指令：${event.payload}`)
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

export function sendGameCommand(command: 'GAME_START' | 'GAME_PAUSE' | 'GAME_STOP'): void {
  const gameStore = useGameStore()
  gameStore.setLastCommand(command)

  if (!socket || socket.readyState !== WebSocket.OPEN) {
    gameStore.setConnectionStatus('error', 'WebSocket 尚未连接，无法发送控制指令。')
    return
  }

  socket.send(JSON.stringify({ cmd: command }))
}
