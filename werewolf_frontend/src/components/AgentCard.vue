<script setup lang="ts">
import type { Agent } from '../stores/game_store'

const props = defineProps<{
  agent: Agent
}>()
</script>

<template>
  <article class="agent-card" :class="[props.agent.status, props.agent.playerType, { revealed: Boolean(props.agent.revealedRole) }]">
    <header>
      <div>
        <h3>{{ props.agent.displayName }}</h3>
        <p>{{ props.agent.visibleRole }} · {{ props.agent.visibleCamp }}</p>
      </div>
      <div class="header-tags">
        <span class="player-type-tag">{{ props.agent.playerType === 'human' ? 'Human' : 'AI' }}</span>
        <span class="status-tag">{{ props.agent.statusLabel }}</span>
      </div>
    </header>

    <section v-if="props.agent.revealedRole" class="reveal-box">
      <h4>公开身份</h4>
      <p>{{ props.agent.revealedRole }}</p>
    </section>

    <section class="meta-badges">
      <span class="meta-badge" :class="props.agent.isAlive ? 'positive' : 'negative'">
        存活：{{ props.agent.isAlive ? '是' : '否' }}
      </span>
      <span class="meta-badge" :class="props.agent.canSpeak ? 'positive' : 'negative'">
        发言：{{ props.agent.canSpeak ? '可' : '不可' }}
      </span>
      <span class="meta-badge" :class="props.agent.canVote ? 'positive' : 'negative'">
        投票：{{ props.agent.canVote ? '可' : '不可' }}
      </span>
    </section>

    <section class="speech-box">
      <h4>当前发言</h4>
      <p>{{ props.agent.currentSpeech || '暂无发言' }}</p>
    </section>

    <section class="history-box">
      <h4>最近发言</h4>
      <ul v-if="props.agent.previousRoundSpeechHistory.length > 0">
        <li v-for="speech in props.agent.previousRoundSpeechHistory" :key="speech">
          {{ speech }}
        </li>
      </ul>
      <p v-else>暂无历史发言</p>
    </section>
  </article>
</template>

<style scoped>
.agent-card {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-height: 100%;
  padding: 16px;
  border-radius: 18px;
  background: #ffffff;
  border: 2px solid transparent;
  box-shadow: 0 16px 36px rgba(15, 23, 42, 0.12);
  color: #111827;
}

.agent-card.human {
  border-color: #fbbf24;
}

.agent-card.alive {
  border-color: #bfdbfe;
}

.agent-card.human.alive {
  border-color: #fbbf24;
}

.agent-card.dead {
  background: #e5e7eb;
  border-color: #f87171;
  color: #4b5563;
}

.agent-card.exiled {
  background: #fef3c7;
  border-color: #f59e0b;
  color: #92400e;
}

.agent-card.revealed {
  box-shadow: 0 18px 40px rgba(245, 158, 11, 0.18);
}

header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.header-tags {
  display: flex;
  flex-direction: column;
  gap: 6px;
  align-items: flex-end;
}

h3,
h4,
p,
ul,
li {
  margin: 0;
  color: inherit;
}

h3 {
  font-size: 1rem;
}

h4 {
  margin-bottom: 8px;
  font-size: 0.95rem;
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

.agent-card.exiled .status-tag {
  background: #fde68a;
  color: #92400e;
}

.reveal-box,
.speech-box,
.history-box {
  padding: 14px;
  border-radius: 14px;
  background: #f8fafc;
  color: #111827;
}

.agent-card.exiled .reveal-box,
.agent-card.exiled .speech-box,
.agent-card.exiled .history-box {
  background: rgba(255, 255, 255, 0.72);
  color: inherit;
}

.meta-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.meta-badge {
  display: inline-flex;
  align-items: center;
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  line-height: 1;
  background: #e2e8f0;
  color: #334155;
}

.meta-badge.positive {
  background: #dcfce7;
  color: #166534;
}

.meta-badge.negative {
  background: #fee2e2;
  color: #991b1b;
}

.agent-card.exiled .meta-badge.positive {
  background: #fef3c7;
  color: #92400e;
}

.agent-card.exiled .meta-badge.negative {
  background: #fde68a;
  color: #92400e;
}

ul {
  padding-left: 18px;
}

li + li {
  margin-top: 6px;
}
</style>
