<script setup lang="ts">
import type { GameMode, RoleConfig, RoleKey } from '../stores/game_store'

const props = defineProps<{
  connectionStatus: string
  connectionMessage: string
  phase: string
  winner: string
  lastCommand: string
  pendingCommand: string
  liveGameStarted: boolean
  canStartGame: boolean
  playerCount: number
  roleCounts: RoleConfig
  gameMode: GameMode
}>()

const emit = defineEmits<{
  start: []
  pause: []
  stop: []
  reset: []
  playerCountChange: [value: number]
  gameModeChange: [value: GameMode]
  randomizeRoles: []
}>()

const roleItems: Array<{ key: RoleKey; label: string }> = [
  { key: 'werewolf', label: '狼人' },
  { key: 'seer', label: '预言家' },
  { key: 'witch', label: '女巫' },
  { key: 'hunter', label: '猎人' },
  { key: 'idiot', label: '白痴' },
  { key: 'villager', label: '村民' },
]
</script>

<template>
  <section class="control-bar">
    <div class="meta-block">
      <span class="label">连接状态</span>
      <strong>{{ props.connectionStatus }}</strong>
      <small>{{ props.connectionMessage }}</small>
    </div>

    <div class="meta-block">
      <span class="label">当前阶段</span>
      <strong>{{ props.phase }}</strong>
      <small v-if="props.phase === '对局结束'">胜者：{{ props.winner || '未收到结果' }}</small>
      <small v-else-if="props.winner">胜者：{{ props.winner }}</small>
      <small v-else-if="props.pendingCommand">等待响应：{{ props.pendingCommand }}</small>
      <small v-else-if="props.liveGameStarted">实时对局进行中</small>
      <small v-else>最近指令：{{ props.lastCommand || '暂无' }}</small>
    </div>

    <div class="meta-block">
      <span class="label">对战模式</span>
      <el-radio-group :model-value="props.gameMode" @update:model-value="(value) => emit('gameModeChange', value as GameMode)">
        <el-radio-button value="ai_only">AI 对战</el-radio-button>
        <el-radio-button value="human_mixed">人机对战</el-radio-button>
      </el-radio-group>
      <small>人机对战模式下固定 1 名人类选手，其余为 AI。</small>
    </div>

    <div class="meta-block">
      <span class="label">玩家人数</span>
      <el-slider
        :min="6"
        :max="12"
        :step="1"
        :model-value="props.playerCount"
        show-stops
        show-input
        input-size="small"
        @update:model-value="(value) => emit('playerCountChange', Number(value))"
      />
      <small>角色配置会随人数自动匹配。</small>
    </div>

    <div class="role-config">
      <div class="role-header">
        <span class="label">角色配置</span>
        <el-button size="small" type="primary" plain @click="emit('randomizeRoles')">随机分配角色</el-button>
      </div>

      <div class="role-grid">
        <div v-for="item in roleItems" :key="item.key" class="role-item">
          <span>{{ item.label }}</span>
          <strong>{{ props.roleCounts[item.key] }}</strong>
        </div>
      </div>
    </div>

    <div class="actions">
      <el-button type="success" :disabled="!props.canStartGame" @click="emit('start')">开始</el-button>
      <el-button type="warning" plain @click="emit('pause')">暂停</el-button>
      <el-button type="danger" plain @click="emit('stop')">结束</el-button>
      <el-button plain @click="emit('reset')">重置对局</el-button>
    </div>
  </section>
</template>

<style scoped>
.control-bar {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
  padding: 20px;
  border-radius: 20px;
  background: rgba(15, 23, 42, 0.86);
  color: #f8fafc;
}

.meta-block,
.role-config {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.label {
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #93c5fd;
}

small {
  color: #cbd5e1;
}

.role-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.role-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 10px;
}

.role-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 12px;
  background: rgba(30, 41, 59, 0.6);
}

.role-item strong {
  color: #f8fafc;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  justify-content: flex-end;
}
</style>
