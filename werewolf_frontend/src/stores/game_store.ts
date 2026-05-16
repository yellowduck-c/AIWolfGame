import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

export type AgentStatus = 'alive' | 'dead' | 'exiled'
export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error'
export type RoleKey = 'werewolf' | 'seer' | 'witch' | 'hunter' | 'villager'
export type GameMode = 'ai_only' | 'human_mixed'

export type Agent = {
  id: number
  role: string
  camp: string
  status: AgentStatus
  currentSpeech: string
  speechHistory: string[]
  playerType: 'ai' | 'human'
  displayName: string
  visibleRole: string
  visibleCamp: string
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

const DEFAULT_HUMAN_SKILL_CONFIG: HumanSkillConfig = {
  mode: 'none',
  title: '无主动技能',
  hint: '当前身份没有可主动释放的技能。',
  placeholder: '',
  buttonText: '提交技能',
  actionLabel: '技能类型',
  emptyMessage: '当前无需执行技能操作。',
}

type MockAgentTemplate = Omit<Agent, 'role' | 'camp' | 'playerType' | 'displayName'>

const ROLE_LABELS: Record<RoleKey, { role: string; camp: string }> = {
  werewolf: { role: '狼人', camp: '狼人' },
  seer: { role: '预言家', camp: '好人' },
  witch: { role: '女巫', camp: '好人' },
  hunter: { role: '猎人', camp: '好人' },
  villager: { role: '村民', camp: '好人' },
}

const DEFAULT_ROLE_CONFIGS: Record<number, RoleConfig> = {
  6: { werewolf: 2, seer: 1, witch: 1, hunter: 0, villager: 2 },
  7: { werewolf: 2, seer: 1, witch: 1, hunter: 1, villager: 2 },
  8: { werewolf: 2, seer: 1, witch: 1, hunter: 1, villager: 3 },
  9: { werewolf: 3, seer: 1, witch: 1, hunter: 1, villager: 3 },
  10: { werewolf: 3, seer: 1, witch: 1, hunter: 1, villager: 4 },
  11: { werewolf: 3, seer: 1, witch: 1, hunter: 1, villager: 5 },
  12: { werewolf: 4, seer: 1, witch: 1, hunter: 1, villager: 5 },
}

const MOCK_AGENT_POOL: MockAgentTemplate[] = [
  { id: 1, status: 'alive', currentSpeech: '我是平民，这轮先看 4 号。', speechHistory: ['我是平民，这轮先看 4 号。', '先别急着站边。'] },
  { id: 2, status: 'alive', currentSpeech: '昨晚我查验了 5 号。', speechHistory: ['昨晚我查验了 5 号。', '今天先从对跳里找狼。'] },
  { id: 3, status: 'alive', currentSpeech: '我先听完发言再决定。', speechHistory: ['我先听完发言再决定。', '目前药还没有交代。'] },
  { id: 4, status: 'alive', currentSpeech: '这轮不要乱投。', speechHistory: ['这轮不要乱投。', '我会盯紧末置位。'] },
  { id: 5, status: 'dead', currentSpeech: '我怀疑 1 号和 6 号。', speechHistory: ['我怀疑 1 号和 6 号。', '我的票会挂在 1 号。'] },
  { id: 6, status: 'alive', currentSpeech: '我建议先看沉默位。', speechHistory: ['我建议先看沉默位。', '今天先出信息少的。'] },
  { id: 7, status: 'alive', currentSpeech: '2 号视角比较完整。', speechHistory: ['2 号视角比较完整。', '我暂时跟 2 号票。'] },
  { id: 8, status: 'alive', currentSpeech: '我想听 9 号和 10 号的解释。', speechHistory: ['我想听 9 号和 10 号的解释。', '后位别再划水了。'] },
  { id: 9, status: 'exiled', currentSpeech: '我不是狼，出我会很亏。', speechHistory: ['我不是狼，出我会很亏。', '你们别被带节奏。'] },
  { id: 10, status: 'alive', currentSpeech: '我会重点看 6 号和 8 号。', speechHistory: ['我会重点看 6 号和 8 号。', '这局要防倒钩。'] },
  { id: 11, status: 'alive', currentSpeech: '我先听 12 号归票。', speechHistory: ['我先听 12 号归票。', '今天先把焦点收紧。'] },
  { id: 12, status: 'alive', currentSpeech: '我觉得 3 号发言不自然。', speechHistory: ['我觉得 3 号发言不自然。', '先看对跳和票型。'] },
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
  const orderedKeys: RoleKey[] = ['werewolf', 'seer', 'witch', 'hunter', 'villager']

  orderedKeys.forEach((key) => {
    for (let index = 0; index < roleConfig[key]; index += 1) {
      sequence.push(key)
    }
  })

  const sliced = sequence.slice(0, playerCount)
  return randomize ? shuffleRoleSequence(sliced) : sliced
}

function createMockAgents(playerCount: number, roleConfig: RoleConfig, randomizeRoles: boolean, gameMode: GameMode): Agent[] {
  const roleSequence = buildRoleSequence(roleConfig, playerCount, randomizeRoles)
  const humanPlayerId = gameMode === 'human_mixed' ? 1 : null
  const humanRoleKey = humanPlayerId === null ? null : roleSequence[humanPlayerId - 1] ?? null

  return MOCK_AGENT_POOL.slice(0, playerCount).map((agent, index) => {
    const roleKey = roleSequence[index] ?? 'villager'
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
      playerType: isHuman ? 'human' : 'ai',
      displayName: isHuman ? '1 号玩家（人类）' : `${agent.id} 号玩家（AI）`,
      visibleRole,
      visibleCamp,
      speechHistory: [...agent.speechHistory],
    }
  })
}

function createMockLogs(agents: Agent[]): SpeakLogEntry[] {
  return agents
    .filter((agent) => agent.id <= Math.min(agents.length, 8))
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

export const useGameStore = defineStore('game', () => {
  const configuredPlayerCount = ref(10)
  const configuredRoleCounts = ref<RoleConfig>(cloneRoleConfig(configuredPlayerCount.value))
  const gameMode = ref<GameMode>('ai_only')
  const agents = ref<Agent[]>(createMockAgents(configuredPlayerCount.value, configuredRoleCounts.value, false, gameMode.value))
  const speakLogs = ref<SpeakLogEntry[]>(createMockLogs(agents.value))
  const currentPhase = ref('day_speech')
  const winner = ref('')
  const connectionStatus = ref<ConnectionStatus>('disconnected')
  const connectionMessage = ref('尚未建立连接。')
  const lastCommand = ref('')
  const humanSpeechDraft = ref('')
  const humanVoteTarget = ref<number | null>(null)
  const humanSkillTarget = ref<number | null>(null)
  const humanSkillAction = ref<HumanSkillAction>('none')

  const aliveCount = computed(() => agents.value.filter((agent) => agent.status === 'alive').length)
  const humanPlayerId = computed(() => (gameMode.value === 'human_mixed' ? 1 : null))
  const humanPlayer = computed(() => agents.value.find((agent) => agent.playerType === 'human') ?? null)
  const humanRoleKey = computed<RoleKey | null>(() => getHumanRoleKey(humanPlayer.value?.role))
  const canUseHunterSkill = computed(() => humanRoleKey.value === 'hunter' && humanPlayer.value?.status !== 'alive')
  const humanSkillConfig = computed<HumanSkillConfig>(() => getHumanSkillConfig(humanRoleKey.value, canUseHunterSkill.value))
  const aliveOtherAgents = computed(() => agents.value.filter((agent) => agent.status === 'alive' && agent.playerType !== 'human'))
  const humanSkillTargets = computed(() => {
    if (humanSkillConfig.value.mode === 'none' || humanSkillConfig.value.mode === 'hunter_wait') {
      return []
    }

    return aliveOtherAgents.value
  })
  const canSubmitHumanSpeech = computed(() => Boolean(humanPlayer.value) && humanSpeechDraft.value.trim().length > 0)
  const canSubmitHumanVote = computed(() => Boolean(humanPlayer.value) && humanVoteTarget.value !== null)
  const canSubmitHumanSkill = computed(() => {
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

  function rebuildMockState(randomizeRoles = false): void {
    agents.value = createMockAgents(configuredPlayerCount.value, configuredRoleCounts.value, randomizeRoles, gameMode.value)
    speakLogs.value = createMockLogs(agents.value)
    winner.value = ''
    currentPhase.value = 'day_speech'
    humanSpeechDraft.value = ''
    humanVoteTarget.value = null
    humanSkillTarget.value = null
    humanSkillAction.value = humanRoleKey.value === 'witch' ? 'heal' : 'none'
  }

  function setConnectionStatus(status: ConnectionStatus, message: string): void {
    connectionStatus.value = status
    connectionMessage.value = message
  }

  function setPhase(phase: string): void {
    currentPhase.value = phase
  }

  function setWinner(nextWinner: string): void {
    winner.value = nextWinner
  }

  function setLastCommand(command: string): void {
    lastCommand.value = command
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

  function initializeAgents(nextAgents: Array<{ id: number; role: string; camp: string; status: AgentStatus }>): void {
    configuredPlayerCount.value = nextAgents.length
    configuredRoleCounts.value = cloneRoleConfig(nextAgents.length)
    agents.value = nextAgents.map((agent) => ({
      ...agent,
      currentSpeech: '',
      speechHistory: [],
      playerType: 'ai',
      displayName: `${agent.id} 号玩家（AI）`,
      visibleRole: agent.role,
      visibleCamp: agent.camp,
    }))
  }

  function appendSpeech(payload: { id: number; role: string; content: string }): void {
    const timestamp = new Date().toLocaleTimeString('zh-CN', { hour12: false })
    const agent = agents.value.find((item) => item.id === payload.id)

    if (agent) {
      agent.currentSpeech = payload.content
      agent.speechHistory.unshift(payload.content)
      agent.speechHistory = agent.speechHistory.slice(0, 5)
    }

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

    if (!agent || !content) {
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

    if (!agent || !target) {
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

    if (!agent) {
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

  function updateAgentStatus(payload: { id: number; status: AgentStatus }): void {
    const agent = agents.value.find((item) => item.id === payload.id)
    if (agent) {
      agent.status = payload.status
    }
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
    aliveOtherAgents,
    agents,
    speakLogs,
    currentPhase,
    winner,
    connectionStatus,
    connectionMessage,
    lastCommand,
    aliveCount,
    setConnectionStatus,
    setPhase,
    setWinner,
    setLastCommand,
    setHumanSpeechDraft,
    setHumanVoteTarget,
    setHumanSkillTarget,
    setHumanSkillAction,
    setConfiguredPlayerCount,
    setGameMode,
    randomizeRoles,
    initializeAgents,
    appendSpeech,
    submitHumanSpeech,
    submitHumanVote,
    submitHumanSkill,
    updateAgentStatus,
  }
})
