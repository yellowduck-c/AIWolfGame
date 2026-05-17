import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

export type AgentStatus = 'alive' | 'dead' | 'exiled'
export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error'
export type RoleKey = 'werewolf' | 'seer' | 'witch' | 'hunter' | 'idiot' | 'villager'
export type GameMode = 'ai_only' | 'human_mixed'

export type Agent = {
  id: number
  role: string
  camp: string
  status: AgentStatus
  currentSpeech: string
  speechHistory: string[]
  speechHistoryRound: number | null
  previousRoundSpeechHistory: string[]
  playerType: 'ai' | 'human'
  displayName: string
  visibleRole: string
  visibleCamp: string
  canVote: boolean
  canSpeak: boolean
  isAlive: boolean
  revealedRole: string | null
  statusLabel: string
}

type AssignedRole = {
  id: number
  role_key: RoleKey
}

export type SpeakLogEntry = {
  timestamp: string
  id: number
  role: string
  content: string
}

export type RoleConfig = Record<RoleKey, number>
export type HumanSkillMode = 'none' | 'single_target' | 'witch' | 'hunter_wait'
export type HumanSkillAction = 'kill' | 'check' | 'heal' | 'poison' | 'shoot' | 'none'

export type HumanSkillConfig = {
  mode: HumanSkillMode
  title: string
  hint: string
  placeholder: string
  buttonText: string
  actionLabel: string
  emptyMessage: string
}

type AgentStatusUpdatePayload = {
  id: number
  status: AgentStatus
  role?: string
  revealed_role?: string
  can_vote?: boolean
  can_speak?: boolean
  is_alive?: boolean
  special?: string
}

const DEFAULT_HUMAN_SKILL_CONFIG: HumanSkillConfig = {
  mode: 'none',
  title: '无主动技能',
  hint: '当前身份没有可主动释放的技能。',
  placeholder: '',
  buttonText: '提交技能',
  actionLabel: '技能类型',
  emptyMessage: '当前无需执行技能操作。',
}

type MockAgentTemplate = Omit<Agent, 'role' | 'camp' | 'playerType' | 'displayName' | 'visibleRole' | 'visibleCamp'>

const ROLE_LABELS: Record<RoleKey, { role: string; camp: string }> = {
  werewolf: { role: '狼人', camp: '狼人' },
  seer: { role: '预言家', camp: '好人' },
  witch: { role: '女巫', camp: '好人' },
  hunter: { role: '猎人', camp: '好人' },
  idiot: { role: '白痴', camp: '好人' },
  villager: { role: '村民', camp: '好人' },
}

const DEFAULT_ROLE_CONFIGS: Record<number, RoleConfig> = {
  6: { werewolf: 2, seer: 1, witch: 0, hunter: 1, idiot: 0, villager: 2 },
  7: { werewolf: 2, seer: 1, witch: 1, hunter: 1, idiot: 0, villager: 2 },
  8: { werewolf: 3, seer: 1, witch: 1, hunter: 1, idiot: 0, villager: 2 },
  9: { werewolf: 3, seer: 1, witch: 1, hunter: 1, idiot: 0, villager: 3 },
  10: { werewolf: 3, seer: 1, witch: 1, hunter: 1, idiot: 0, villager: 4 },
  11: { werewolf: 4, seer: 1, witch: 1, hunter: 1, idiot: 1, villager: 3 },
  12: { werewolf: 4, seer: 1, witch: 1, hunter: 1, idiot: 1, villager: 4 },
}

const MOCK_AGENT_POOL: MockAgentTemplate[] = [
  { id: 1, status: 'alive', currentSpeech: '', speechHistory: [], speechHistoryRound: null, previousRoundSpeechHistory: [], canVote: true, canSpeak: true, isAlive: true, revealedRole: null, statusLabel: '存活' },
  { id: 2, status: 'alive', currentSpeech: '', speechHistory: [], speechHistoryRound: null, previousRoundSpeechHistory: [], canVote: true, canSpeak: true, isAlive: true, revealedRole: null, statusLabel: '存活' },
  { id: 3, status: 'alive', currentSpeech: '', speechHistory: [], speechHistoryRound: null, previousRoundSpeechHistory: [], canVote: true, canSpeak: true, isAlive: true, revealedRole: null, statusLabel: '存活' },
  { id: 4, status: 'alive', currentSpeech: '', speechHistory: [], speechHistoryRound: null, previousRoundSpeechHistory: [], canVote: true, canSpeak: true, isAlive: true, revealedRole: null, statusLabel: '存活' },
  { id: 5, status: 'alive', currentSpeech: '', speechHistory: [], speechHistoryRound: null, previousRoundSpeechHistory: [], canVote: true, canSpeak: true, isAlive: true, revealedRole: null, statusLabel: '存活' },
  { id: 6, status: 'alive', currentSpeech: '', speechHistory: [], speechHistoryRound: null, previousRoundSpeechHistory: [], canVote: true, canSpeak: true, isAlive: true, revealedRole: null, statusLabel: '存活' },
  { id: 7, status: 'alive', currentSpeech: '', speechHistory: [], speechHistoryRound: null, previousRoundSpeechHistory: [], canVote: true, canSpeak: true, isAlive: true, revealedRole: null, statusLabel: '存活' },
  { id: 8, status: 'alive', currentSpeech: '', speechHistory: [], speechHistoryRound: null, previousRoundSpeechHistory: [], canVote: true, canSpeak: true, isAlive: true, revealedRole: null, statusLabel: '存活' },
  { id: 9, status: 'alive', currentSpeech: '', speechHistory: [], speechHistoryRound: null, previousRoundSpeechHistory: [], canVote: true, canSpeak: true, isAlive: true, revealedRole: null, statusLabel: '存活' },
  { id: 10, status: 'alive', currentSpeech: '', speechHistory: [], speechHistoryRound: null, previousRoundSpeechHistory: [], canVote: true, canSpeak: true, isAlive: true, revealedRole: null, statusLabel: '存活' },
  { id: 11, status: 'alive', currentSpeech: '', speechHistory: [], speechHistoryRound: null, previousRoundSpeechHistory: [], canVote: true, canSpeak: true, isAlive: true, revealedRole: null, statusLabel: '存活' },
  { id: 12, status: 'alive', currentSpeech: '', speechHistory: [], speechHistoryRound: null, previousRoundSpeechHistory: [], canVote: true, canSpeak: true, isAlive: true, revealedRole: null, statusLabel: '存活' },
]

function cloneRoleConfig(playerCount: number): RoleConfig {
  return { ...DEFAULT_ROLE_CONFIGS[playerCount] }
}

function shuffleRoleSequence(roleSequence: RoleKey[]): RoleKey[] {
  const shuffled = [...roleSequence]

  for (let index = shuffled.length - 1; index > 0; index -= 1) {
    const swapIndex = Math.floor(Math.random() * (index + 1))
    ;[shuffled[index], shuffled[swapIndex]] = [shuffled[swapIndex], shuffled[index]]
  }

  return shuffled
}

function buildRoleSequence(roleConfig: RoleConfig, playerCount: number, randomize: boolean): RoleKey[] {
  const sequence: RoleKey[] = []
  const orderedKeys: RoleKey[] = ['werewolf', 'seer', 'witch', 'hunter', 'idiot', 'villager']

  orderedKeys.forEach((key) => {
    for (let index = 0; index < roleConfig[key]; index += 1) {
      sequence.push(key)
    }
  })

  const sliced = sequence.slice(0, playerCount)
  return randomize ? shuffleRoleSequence(sliced) : sliced
}

function createAssignedRoles(playerCount: number, roleConfig: RoleConfig, randomizeRoles: boolean): AssignedRole[] {
  const roleSequence = buildRoleSequence(roleConfig, playerCount, randomizeRoles)
  return roleSequence.map((roleKey, index) => ({
    id: index + 1,
    role_key: roleKey,
  }))
}

function getStatusLabel(status: AgentStatus, revealedRole: string | null = null): string {
  if (status === 'dead') {
    return '死亡'
  }
  if (status === 'exiled') {
    return revealedRole === '白痴' ? '白痴已放逐' : '放逐'
  }
  return '存活'
}

function createMockAgentsFromAssignments(assignedRoles: AssignedRole[], gameMode: GameMode): Agent[] {
  const humanPlayerId = gameMode === 'human_mixed' ? 1 : null
  const humanRoleKey = humanPlayerId === null ? null : assignedRoles.find((assignment) => assignment.id === humanPlayerId)?.role_key ?? null

  return MOCK_AGENT_POOL.slice(0, assignedRoles.length).map((agent, index) => {
    const roleKey = assignedRoles[index]?.role_key ?? 'villager'
    const roleMeta = ROLE_LABELS[roleKey]
    const isHuman = humanPlayerId === agent.id
    const visibleRole = gameMode === 'ai_only' || isHuman || (humanRoleKey === 'werewolf' && roleKey === 'werewolf')
      ? roleMeta.role
      : '未知身份'
    const visibleCamp = gameMode === 'ai_only' || isHuman || (humanRoleKey === 'werewolf' && roleKey === 'werewolf')
      ? roleMeta.camp
      : '未知阵营'

    return {
      ...agent,
      role: roleMeta.role,
      camp: roleMeta.camp,
      status: 'alive',
      currentSpeech: '',
      speechHistory: [],
      speechHistoryRound: null,
      previousRoundSpeechHistory: [],
      playerType: isHuman ? 'human' : 'ai',
      displayName: isHuman ? '1 号玩家（人类）' : `${agent.id} 号玩家（AI）`,
      visibleRole,
      visibleCamp,
      canVote: true,
      canSpeak: true,
      isAlive: true,
      revealedRole: null,
      statusLabel: getStatusLabel('alive'),
    }
  })
}

function createMockAgents(playerCount: number, roleConfig: RoleConfig, randomizeRoles: boolean, gameMode: GameMode): Agent[] {
  const assignedRoles = createAssignedRoles(playerCount, roleConfig, randomizeRoles)
  return createMockAgentsFromAssignments(assignedRoles, gameMode)
}

function createEmptyAgents(playerCount: number, gameMode: GameMode): Agent[] {
  const humanPlayerId = gameMode === 'human_mixed' ? 1 : null

  return MOCK_AGENT_POOL.slice(0, playerCount).map((agent) => {
    const isHuman = humanPlayerId === agent.id
    return {
      ...agent,
      role: '',
      camp: '',
      status: 'alive',
      currentSpeech: '',
      speechHistory: [],
      speechHistoryRound: null,
      previousRoundSpeechHistory: [],
      playerType: isHuman ? 'human' : 'ai',
      displayName: isHuman ? '1 号玩家（人类）' : `${agent.id} 号玩家（AI）`,
      visibleRole: '',
      visibleCamp: '',
      canVote: true,
      canSpeak: true,
      isAlive: true,
      revealedRole: null,
      statusLabel: getStatusLabel('alive'),
    }
  })
}

function createMockLogs(agents: Agent[]): SpeakLogEntry[] {
  return agents
    .filter((agent) => agent.id <= Math.min(agents.length, 8) && agent.currentSpeech)
    .map((agent, index) => ({
      timestamp: `20:00:${String(index * 7 + 1).padStart(2, '0')}`,
      id: agent.id,
      role: agent.role,
      content: agent.currentSpeech,
    }))
}

function getHumanRoleKey(role: string | null | undefined): RoleKey | null {
  const entry = Object.entries(ROLE_LABELS).find(([, meta]) => meta.role === role)
  return (entry?.[0] as RoleKey | undefined) ?? null
}

function getHumanSkillConfig(roleKey: RoleKey | null, canUseHunterSkill: boolean): HumanSkillConfig {
  switch (roleKey) {
    case 'werewolf':
      return {
        mode: 'single_target',
        title: '狼人击杀',
        hint: '选择一名存活的其他玩家，模拟狼人夜间击杀目标。',
        placeholder: '请选择击杀目标',
        buttonText: '确认击杀',
        actionLabel: '技能类型',
        emptyMessage: '暂无可选击杀目标。',
      }
    case 'seer':
      return {
        mode: 'single_target',
        title: '预言家查验',
        hint: '选择一名存活的其他玩家，模拟本轮查验对象。',
        placeholder: '请选择查验目标',
        buttonText: '确认查验',
        actionLabel: '技能类型',
        emptyMessage: '暂无可选查验目标。',
      }
    case 'witch':
      return {
        mode: 'witch',
        title: '女巫技能',
        hint: '可选择使用解药或毒药；毒药需要指定一名存活目标。',
        placeholder: '请选择毒药目标',
        buttonText: '确认技能',
        actionLabel: '药剂选择',
        emptyMessage: '当前没有可用的女巫技能目标。',
      }
    case 'hunter':
      return canUseHunterSkill
        ? {
            mode: 'single_target',
            title: '猎人开枪',
            hint: '你已满足开枪条件，可选择一名其他存活玩家作为目标。',
            placeholder: '请选择开枪目标',
            buttonText: '确认开枪',
            actionLabel: '技能类型',
            emptyMessage: '暂无可选开枪目标。',
          }
        : {
            mode: 'hunter_wait',
            title: '猎人技能待命',
            hint: '猎人仅在死亡触发时可以开枪，当前阶段不可主动使用。',
            placeholder: '',
            buttonText: '确认开枪',
            actionLabel: '技能类型',
            emptyMessage: '当前未满足猎人开枪条件。',
          }
    case 'villager':
    default:
      return DEFAULT_HUMAN_SKILL_CONFIG
  }
}

function hasAssignedIdentity(agents: Agent[]): boolean {
  return agents.length > 0 && agents.every((agent) => Boolean(agent.role && agent.camp))
}

export const useGameStore = defineStore('game', () => {
  const configuredPlayerCount = ref(10)
  const configuredRoleCounts = ref<RoleConfig>(cloneRoleConfig(configuredPlayerCount.value))
  const assignedRoles = ref<AssignedRole[]>(createAssignedRoles(configuredPlayerCount.value, configuredRoleCounts.value, false))
  const gameMode = ref<GameMode>('ai_only')
  const agents = ref<Agent[]>(createMockAgents(configuredPlayerCount.value, configuredRoleCounts.value, false, gameMode.value))
  const speakLogs = ref<SpeakLogEntry[]>(createMockLogs(agents.value))
  const currentPhase = ref('day_speech')
  const currentRound = ref(1)
  const currentGameId = ref('')
  const winner = ref('')
  const connectionStatus = ref<ConnectionStatus>('disconnected')
  const connectionMessage = ref('尚未建立连接。')
  const lastCommand = ref('')
  const pendingCommand = ref('')
  const liveGameStarted = ref(false)
  const humanSpeechDraft = ref('')
  const humanVoteTarget = ref<number | null>(null)
  const humanSkillTarget = ref<number | null>(null)
  const humanSkillAction = ref<HumanSkillAction>('none')

  const aliveCount = computed(() => agents.value.filter((agent) => agent.isAlive).length)
  const humanPlayerId = computed(() => (gameMode.value === 'human_mixed' ? 1 : null))
  const humanPlayer = computed(() => agents.value.find((agent) => agent.playerType === 'human') ?? null)
  const humanRoleKey = computed<RoleKey | null>(() => getHumanRoleKey(humanPlayer.value?.role))
  const canUseHunterSkill = computed(() => humanRoleKey.value === 'hunter' && humanPlayer.value?.status !== 'alive')
  const humanSkillConfig = computed<HumanSkillConfig>(() => getHumanSkillConfig(humanRoleKey.value, canUseHunterSkill.value))
  const aliveOtherAgents = computed(() => agents.value.filter((agent) => agent.isAlive && agent.playerType !== 'human'))
  const humanSkillTargets = computed(() => {
    if (humanSkillConfig.value.mode === 'none' || humanSkillConfig.value.mode === 'hunter_wait') {
      return []
    }

    return aliveOtherAgents.value
  })
  const canSubmitHumanSpeech = computed(() => Boolean(humanPlayer.value?.canSpeak) && humanSpeechDraft.value.trim().length > 0)
  const canSubmitHumanVote = computed(() => Boolean(humanPlayer.value?.canVote) && humanVoteTarget.value !== null)
  const canSubmitHumanSkill = computed(() => {
    if (!humanPlayer.value?.isAlive) {
      return false
    }

    switch (humanRoleKey.value) {
      case 'werewolf':
      case 'seer':
        return humanSkillTarget.value !== null
      case 'witch':
        return humanSkillAction.value === 'heal' || (humanSkillAction.value === 'poison' && humanSkillTarget.value !== null)
      case 'hunter':
        return canUseHunterSkill.value && humanSkillTarget.value !== null
      default:
        return false
    }
  })
  const canStartGame = computed(() => connectionStatus.value === 'connected' && !pendingCommand.value)

  function rebuildMockState(randomizeRoles = false): void {
    assignedRoles.value = createAssignedRoles(configuredPlayerCount.value, configuredRoleCounts.value, randomizeRoles)
    agents.value = createMockAgentsFromAssignments(assignedRoles.value, gameMode.value)
    speakLogs.value = createMockLogs(agents.value)
    winner.value = ''
    currentGameId.value = ''
    currentPhase.value = 'day_speech'
    currentRound.value = 1
    pendingCommand.value = ''
    liveGameStarted.value = false
    humanSpeechDraft.value = ''
    humanVoteTarget.value = null
    humanSkillTarget.value = null
    humanSkillAction.value = humanRoleKey.value === 'witch' ? 'heal' : 'none'
  }

  function setConnectionStatus(status: ConnectionStatus, message: string): void {
    connectionStatus.value = status
    connectionMessage.value = message
  }

  function setPhase(phase: string, round?: number): void {
    const previousRound = currentRound.value
    const previousPhase = currentPhase.value
    currentPhase.value = phase
    if (typeof round === 'number' && Number.isFinite(round)) {
      currentRound.value = round
    }
    if (phase === 'day_speech' && (currentRound.value !== previousRound || previousPhase !== 'day_speech')) {
      agents.value = agents.value.map((agent) => {
        if (currentRound.value <= 1) {
          return {
            ...agent,
            currentSpeech: '',
            previousRoundSpeechHistory: [],
            speechHistory: [],
            speechHistoryRound: currentRound.value,
          }
        }

        if (currentRound.value !== previousRound) {
          return {
            ...agent,
            currentSpeech: '',
            previousRoundSpeechHistory: agent.speechHistoryRound === previousRound ? [...agent.speechHistory] : [],
            speechHistory: [],
            speechHistoryRound: currentRound.value,
          }
        }

        return {
          ...agent,
          currentSpeech: '',
          previousRoundSpeechHistory: agent.speechHistoryRound === currentRound.value - 1 ? [...agent.speechHistory] : agent.previousRoundSpeechHistory,
        }
      })
    }
  }

  function setCurrentGameId(gameId: string): void {
    currentGameId.value = gameId
  }

  function setWinner(nextWinner: string): void {
    winner.value = nextWinner
  }

  function setLastCommand(command: string): void {
    lastCommand.value = command
  }

  function setPendingCommand(command: string): void {
    pendingCommand.value = command
  }

  function clearPendingCommand(): void {
    pendingCommand.value = ''
  }

  function setLiveGameStarted(started: boolean): void {
    liveGameStarted.value = started
  }

  function setHumanSpeechDraft(content: string): void {
    humanSpeechDraft.value = content
  }

  function setHumanVoteTarget(target: number | null): void {
    humanVoteTarget.value = target
  }

  function setHumanSkillTarget(target: number | null): void {
    humanSkillTarget.value = target
  }

  function setHumanSkillAction(action: HumanSkillAction): void {
    humanSkillAction.value = action
    if (action !== 'poison') {
      humanSkillTarget.value = null
    }
  }

  function setConfiguredPlayerCount(playerCount: number): void {
    configuredPlayerCount.value = playerCount
    configuredRoleCounts.value = cloneRoleConfig(playerCount)
    rebuildMockState()
  }

  function setGameMode(mode: GameMode): void {
    gameMode.value = mode
    rebuildMockState()
  }

  function randomizeRoles(): void {
    rebuildMockState(true)
  }

  function buildGameStartConfig(): { player_count: number; role_counts: RoleConfig; assigned_roles: AssignedRole[] } {
    if (!hasAssignedIdentity(agents.value)) {
      rebuildMockState(true)
    }

    if (assignedRoles.value.length !== configuredPlayerCount.value) {
      assignedRoles.value = createAssignedRoles(configuredPlayerCount.value, configuredRoleCounts.value, false)
    }

    return {
      player_count: configuredPlayerCount.value,
      role_counts: { ...configuredRoleCounts.value },
      assigned_roles: assignedRoles.value.map((assignment) => ({ ...assignment })),
    }
  }

  function initializeAgents(nextAgents: Array<{ id: number; role: string; camp: string; status: AgentStatus }>): void {
    configuredPlayerCount.value = nextAgents.length
    configuredRoleCounts.value = cloneRoleConfig(nextAgents.length)
    currentPhase.value = 'night'
    currentRound.value = 1
    winner.value = ''
    speakLogs.value = []
    liveGameStarted.value = true
    pendingCommand.value = ''
    agents.value = nextAgents.map((agent) => ({
      ...agent,
      currentSpeech: '',
      speechHistory: [],
      speechHistoryRound: null,
      previousRoundSpeechHistory: [],
      playerType: gameMode.value === 'human_mixed' && agent.id === 1 ? 'human' : 'ai',
      displayName: gameMode.value === 'human_mixed' && agent.id === 1 ? '1 号玩家（人类）' : `${agent.id} 号玩家（AI）`,
      visibleRole: agent.role,
      visibleCamp: agent.camp,
      canVote: true,
      canSpeak: true,
      isAlive: agent.status === 'alive',
      revealedRole: null,
      statusLabel: getStatusLabel(agent.status),
    }))
  }

  function resetGameState(): void {
    assignedRoles.value = []
    agents.value = createEmptyAgents(configuredPlayerCount.value, gameMode.value)
    speakLogs.value = []
    currentPhase.value = ''
    currentRound.value = 1
    currentGameId.value = ''
    winner.value = ''
    pendingCommand.value = ''
    liveGameStarted.value = false
    humanSpeechDraft.value = ''
    humanVoteTarget.value = null
    humanSkillTarget.value = null
    humanSkillAction.value = 'none'
  }

  function updateStreamingSpeech(payload: { id: number; content: string }): void {
    agents.value = agents.value.map((agent) => {
      if (agent.id !== payload.id) {
        return agent
      }

      return {
        ...agent,
        currentSpeech: payload.content,
      }
    })
  }

  function appendSpeech(payload: { id: number; role: string; content: string }): void {
    const timestamp = new Date().toLocaleTimeString('zh-CN', { hour12: false })
    const historyRound = currentRound.value

    agents.value = agents.value.map((agent) => {
      if (agent.id !== payload.id) {
        return agent
      }

      const sameRoundHistory = agent.speechHistoryRound === historyRound ? agent.speechHistory : []
      return {
        ...agent,
        currentSpeech: payload.content,
        speechHistoryRound: historyRound,
        speechHistory: [payload.content, ...sameRoundHistory],
      }
    })

    speakLogs.value.unshift({
      timestamp,
      id: payload.id,
      role: payload.role,
      content: payload.content,
    })
  }

  function appendSystemLog(payload: { id: number; role: string; content: string }): void {
    const timestamp = new Date().toLocaleTimeString('zh-CN', { hour12: false })

    speakLogs.value.unshift({
      timestamp,
      id: payload.id,
      role: payload.role,
      content: payload.content,
    })
  }

  function submitHumanSpeech(): void {
    const agent = humanPlayer.value
    const content = humanSpeechDraft.value.trim()

    if (!agent || !agent.canSpeak || !content) {
      return
    }

    appendSpeech({
      id: agent.id,
      role: agent.role,
      content,
    })
    humanSpeechDraft.value = ''
  }

  function submitHumanVote(): void {
    const agent = humanPlayer.value
    const targetId = humanVoteTarget.value
    const target = agents.value.find((item) => item.id === targetId)

    if (!agent || !agent.canVote || !target) {
      return
    }

    appendSpeech({
      id: agent.id,
      role: agent.role,
      content: `我投票给 ${target.id} 号玩家。`,
    })
    lastCommand.value = `HUMAN_VOTE:${target.id}`
    humanVoteTarget.value = null
  }

  function submitHumanSkill(): void {
    const agent = humanPlayer.value
    const targetId = humanSkillTarget.value
    const target = agents.value.find((item) => item.id === targetId)

    if (!agent || !agent.isAlive) {
      return
    }

    switch (humanRoleKey.value) {
      case 'werewolf':
        if (!target) {
          return
        }
        appendSpeech({
          id: agent.id,
          role: agent.role,
          content: `我决定今晚击杀 ${target.id} 号玩家。`,
        })
        lastCommand.value = `HUMAN_WEREWOLF_KILL:${target.id}`
        humanSkillTarget.value = null
        return
      case 'seer':
        if (!target) {
          return
        }
        appendSpeech({
          id: agent.id,
          role: agent.role,
          content: `我选择查验 ${target.id} 号玩家。`,
        })
        lastCommand.value = `HUMAN_SEER_CHECK:${target.id}`
        humanSkillTarget.value = null
        return
      case 'witch':
        if (humanSkillAction.value === 'heal') {
          appendSpeech({
            id: agent.id,
            role: agent.role,
            content: '我决定使用解药救人。',
          })
          lastCommand.value = 'HUMAN_WITCH_HEAL'
          return
        }

        if (humanSkillAction.value === 'poison' && target) {
          appendSpeech({
            id: agent.id,
            role: agent.role,
            content: `我决定对 ${target.id} 号玩家使用毒药。`,
          })
          lastCommand.value = `HUMAN_WITCH_POISON:${target.id}`
          humanSkillTarget.value = null
        }
        return
      case 'hunter':
        if (!canUseHunterSkill.value || !target) {
          return
        }
        appendSpeech({
          id: agent.id,
          role: agent.role,
          content: `我发动猎人技能，带走 ${target.id} 号玩家。`,
        })
        lastCommand.value = `HUMAN_HUNTER_SHOOT:${target.id}`
        humanSkillTarget.value = null
        return
      default:
        return
    }
  }

  function updateAgentStatus(payload: AgentStatusUpdatePayload): void {
    agents.value = agents.value.map((agent) => {
      if (agent.id !== payload.id) {
        return agent
      }

      const revealedRole = payload.revealed_role ?? agent.revealedRole
      const visibleRole = revealedRole ?? agent.visibleRole
      return {
        ...agent,
        status: payload.status,
        visibleRole,
        canVote: payload.can_vote ?? (payload.status === 'alive'),
        canSpeak: payload.can_speak ?? (payload.status === 'alive'),
        isAlive: payload.is_alive ?? (payload.status === 'alive'),
        revealedRole,
        statusLabel: getStatusLabel(payload.status, revealedRole),
      }
    })
  }

  return {
    configuredPlayerCount,
    configuredRoleCounts,
    gameMode,
    humanPlayerId,
    humanPlayer,
    humanSpeechDraft,
    humanVoteTarget,
    humanSkillTarget,
    humanSkillAction,
    humanRoleKey,
    humanSkillConfig,
    humanSkillTargets,
    canSubmitHumanSpeech,
    canSubmitHumanVote,
    canSubmitHumanSkill,
    canStartGame,
    aliveOtherAgents,
    agents,
    speakLogs,
    currentPhase,
    currentRound,
    currentGameId,
    winner,
    connectionStatus,
    connectionMessage,
    lastCommand,
    pendingCommand,
    liveGameStarted,
    aliveCount,
    setConnectionStatus,
    setPhase,
    setCurrentGameId,
    setWinner,
    setLastCommand,
    setPendingCommand,
    clearPendingCommand,
    setLiveGameStarted,
    setHumanSpeechDraft,
    setHumanVoteTarget,
    setHumanSkillTarget,
    setHumanSkillAction,
    setConfiguredPlayerCount,
    setGameMode,
    randomizeRoles,
    buildGameStartConfig,
    initializeAgents,
    resetGameState,
    appendSpeech,
    updateStreamingSpeech,
    appendSystemLog,
    submitHumanSpeech,
    submitHumanVote,
    submitHumanSkill,
    updateAgentStatus,
  }
})
