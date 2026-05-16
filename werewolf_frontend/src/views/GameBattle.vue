<script setup lang="ts">
import { storeToRefs } from 'pinia'
import { computed, onMounted } from 'vue'

import AgentGrid from '../components/AgentGrid.vue'
import GameControlBar from '../components/GameControlBar.vue'
import SpeakLogPanel from '../components/SpeakLogPanel.vue'
import type { GameMode } from '../stores/game_store'
import { useGameStore } from '../stores/game_store'
import { apiBaseUrl, connectGameWebSocket, sendGameCommand, wsBaseUrl } from '../utils/websocket'

const gameStore = useGameStore()
const {
  agents,
  speakLogs,
  currentPhase,
  winner,
  connectionStatus,
  connectionMessage,
  lastCommand,
  aliveCount,
  configuredPlayerCount,
  configuredRoleCounts,
  gameMode,
  humanPlayer,
  humanSpeechDraft,
  humanVoteTarget,
  humanSkillTarget,
  humanSkillAction,
  humanSkillConfig,
  humanSkillTargets,
  canSubmitHumanSpeech,
  canSubmitHumanVote,
  canSubmitHumanSkill,
  aliveOtherAgents,
} = storeToRefs(gameStore)

const phaseLabel = computed(() => {
  const labels: Record<string, string> = {
    night: '夜晚行动',
    day_speech: '白天发言',
    voting: '投票放逐',
    finished: '对局结束',
  }

  return labels[currentPhase.value] ?? currentPhase.value
})

function handleStart(): void {
  sendGameCommand('GAME_START')
}

function handlePause(): void {
  sendGameCommand('GAME_PAUSE')
}

function handleStop(): void {
  sendGameCommand('GAME_STOP')
}

function handlePlayerCountChange(value: number): void {
  gameStore.setConfiguredPlayerCount(value)
}

function handleGameModeChange(value: GameMode): void {
  gameStore.setGameMode(value)
}

function handleRandomizeRoles(): void {
  gameStore.randomizeRoles()
}

function handleHumanSpeechSubmit(): void {
  gameStore.submitHumanSpeech()
}

function handleHumanVoteSubmit(): void {
  gameStore.submitHumanVote()
}

function handleHumanSkillSubmit(): void {
  gameStore.submitHumanSkill()
}

onMounted(() => {
  connectGameWebSocket()
})
</script>

<template>
  <main class="battle-page">
    <section class="page-header">
      <div>
        <p class="eyebrow">God View Dashboard</p>
        <h1>AI 狼人杀对局观战台</h1>
        <p class="subtitle">
          已存活 {{ aliveCount }} / {{ agents.length }} 人 · 当前阶段：{{ phaseLabel }}
        </p>
      </div>

      <div class="endpoint-box">
        <p><strong>HTTP:</strong> {{ apiBaseUrl }}</p>
        <p><strong>WebSocket:</strong> {{ wsBaseUrl }}</p>
      </div>
    </section>

    <GameControlBar
      :connection-status="connectionStatus"
      :connection-message="connectionMessage"
      :phase="phaseLabel"
      :winner="winner"
      :last-command="lastCommand"
      :player-count="configuredPlayerCount"
      :role-counts="configuredRoleCounts"
      :game-mode="gameMode"
      @start="handleStart"
      @pause="handlePause"
      @stop="handleStop"
      @player-count-change="handlePlayerCountChange"
      @game-mode-change="handleGameModeChange"
      @randomize-roles="handleRandomizeRoles"
    />

    <section v-if="gameMode === 'human_mixed' && humanPlayer" class="human-action-panel">
      <section class="human-speech-panel human-identity-panel">
        <div>
          <p class="eyebrow">Human Role</p>
          <h2>{{ humanPlayer.displayName }} 身份牌</h2>
          <p class="human-hint">这里会固定展示你当前可见的身份与阵营信息，方便在人机对战中随时确认自己的角色。</p>
        </div>

        <article class="identity-card" :class="[humanPlayer.status, humanPlayer.playerType]">
          <header class="identity-card-header">
            <div>
              <h3>{{ humanPlayer.displayName }}</h3>
              <p>{{ humanPlayer.visibleRole }} · {{ humanPlayer.visibleCamp }}</p>
            </div>
            <div class="header-tags">
              <span class="player-type-tag">Human</span>
              <span class="status-tag">{{ humanPlayer.status }}</span>
            </div>
          </header>
        </article>
      </section>

      <section class="human-speech-panel">
        <div>
          <p class="eyebrow">Human Input</p>
          <h2>{{ humanPlayer.displayName }} 发言</h2>
          <p class="human-hint">在这里输入人类玩家的发言内容，提交后会同步写入玩家卡片和全局发言流。</p>
        </div>

        <div class="human-speech-controls">
          <el-input
            :model-value="humanSpeechDraft"
            type="textarea"
            :rows="3"
            maxlength="120"
            show-word-limit
            placeholder="请输入人类玩家的发言内容..."
            @update:model-value="(value) => gameStore.setHumanSpeechDraft(String(value))"
          />
          <el-button type="primary" :disabled="!canSubmitHumanSpeech" @click="handleHumanSpeechSubmit">提交发言</el-button>
        </div>
      </section>

      <section class="human-speech-panel">
        <div>
          <p class="eyebrow">Human Vote</p>
          <h2>{{ humanPlayer.displayName }} 投票</h2>
          <p class="human-hint">选择一名仍然存活的其他玩家，提交你的投票决定。</p>
        </div>

        <div class="human-speech-controls">
          <el-select
            :model-value="humanVoteTarget"
            placeholder="请选择投票目标"
            @update:model-value="(value) => gameStore.setHumanVoteTarget(Number(value))"
          >
            <el-option v-for="agent in aliveOtherAgents" :key="agent.id" :label="agent.displayName" :value="agent.id" />
          </el-select>
          <el-button type="warning" :disabled="!canSubmitHumanVote" @click="handleHumanVoteSubmit">提交投票</el-button>
        </div>
      </section>

      <section class="human-speech-panel">
        <div>
          <p class="eyebrow">Human Skill</p>
          <h2>{{ humanPlayer.displayName }} {{ humanSkillConfig.title }}</h2>
          <p class="human-hint">{{ humanSkillConfig.hint }}</p>
        </div>

        <div class="human-speech-controls">
          <template v-if="humanSkillConfig.mode === 'single_target'">
            <el-select
              :model-value="humanSkillTarget"
              :placeholder="humanSkillConfig.placeholder"
              @update:model-value="(value) => gameStore.setHumanSkillTarget(Number(value))"
            >
              <el-option v-for="agent in humanSkillTargets" :key="agent.id" :label="agent.displayName" :value="agent.id" />
            </el-select>
            <el-button type="success" :disabled="!canSubmitHumanSkill" @click="handleHumanSkillSubmit">{{ humanSkillConfig.buttonText }}</el-button>
          </template>

          <template v-else-if="humanSkillConfig.mode === 'witch'">
            <el-radio-group
              :model-value="humanSkillAction"
              @update:model-value="(value) => gameStore.setHumanSkillAction(String(value) as 'heal' | 'poison')"
            >
              <el-radio-button value="heal">解药</el-radio-button>
              <el-radio-button value="poison">毒药</el-radio-button>
            </el-radio-group>

            <el-select
              v-if="humanSkillAction === 'poison'"
              :model-value="humanSkillTarget"
              :placeholder="humanSkillConfig.placeholder"
              @update:model-value="(value) => gameStore.setHumanSkillTarget(Number(value))"
            >
              <el-option v-for="agent in humanSkillTargets" :key="agent.id" :label="agent.displayName" :value="agent.id" />
            </el-select>

            <el-button type="success" :disabled="!canSubmitHumanSkill" @click="handleHumanSkillSubmit">{{ humanSkillConfig.buttonText }}</el-button>
          </template>

          <template v-else>
            <p class="human-skill-empty">{{ humanSkillConfig.emptyMessage }}</p>
          </template>
        </div>
      </section>
    </section>

    <section class="content-grid">
      <AgentGrid :agents="agents" />
      <SpeakLogPanel :logs="speakLogs" />
    </section>
  </main>
</template>

<style scoped>
.battle-page {
  min-height: 100vh;
  padding: 24px;
  background: linear-gradient(180deg, #0f172a 0%, #172554 100%);
  color: #f8fafc;
}

.page-header {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 24px;
}

.eyebrow {
  margin: 0 0 6px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #93c5fd;
}

h1,
h2 {
  margin: 0;
}

h1 {
  font-size: clamp(2rem, 4vw, 3rem);
}

.subtitle,
.endpoint-box p,
.human-hint,
.human-skill-empty {
  margin: 8px 0 0;
  color: #cbd5e1;
}

.endpoint-box,
.human-speech-panel {
  padding: 16px 18px;
  border-radius: 18px;
  background: rgba(15, 23, 42, 0.72);
}

.human-identity-panel {
  align-items: stretch;
}

.identity-card {
  flex: 1;
  min-width: min(100%, 320px);
  padding: 16px;
  border-radius: 18px;
  background: #ffffff;
  border: 2px solid transparent;
  box-shadow: 0 16px 36px rgba(15, 23, 42, 0.12);
  color: #0f172a;
}

.identity-card.human {
  border-color: #fbbf24;
}

.identity-card.alive {
  border-color: #bfdbfe;
}

.identity-card.human.alive {
  border-color: #fbbf24;
}

.identity-card.dead,
.identity-card.exiled {
  background: #e5e7eb;
  border-color: #f87171;
  color: #4b5563;
}

.identity-card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.identity-card-header h3,
.identity-card-header p {
  margin: 0;
}

.header-tags {
  display: flex;
  flex-direction: column;
  gap: 6px;
  align-items: flex-end;
}

.player-type-tag,
.status-tag {
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  text-transform: uppercase;
}

.player-type-tag {
  background: #fef3c7;
  color: #b45309;
}

.status-tag {
  background: #dbeafe;
  color: #1d4ed8;
}

.human-action-panel {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 16px;
  margin-top: 24px;
}

.human-speech-panel {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-top: 24px;
}

.human-speech-controls {
  display: flex;
  flex: 1;
  min-width: min(100%, 420px);
  flex-direction: column;
  gap: 12px;
}

.content-grid {
  display: grid;
  grid-template-columns: minmax(0, 2.6fr) minmax(320px, 1fr);
  gap: 20px;
  margin-top: 24px;
}

@media (max-width: 1360px) {
  .content-grid {
    grid-template-columns: 1fr;
  }
}
</style>
