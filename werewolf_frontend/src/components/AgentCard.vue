<script setup lang="ts">
import type { Agent } from '../stores/game_store'

const props = defineProps<{
  agent: Agent
}>()
</script>

<template>
  <article class="agent-card" :class="[props.agent.status, props.agent.playerType]">
    <header>
      <div>
        <h3>{{ props.agent.displayName }}</h3>
        <p>{{ props.agent.visibleRole }} · {{ props.agent.visibleCamp }}</p>
      </div>
      <div class="header-tags">
        <span class="player-type-tag">{{ props.agent.playerType === 'human' ? 'Human' : 'AI' }}</span>
        <span class="status-tag">{{ props.agent.status }}</span>
      </div>
    </header>

    <section class="speech-box">
      <h4>当前发言</h4>
      <p>{{ props.agent.currentSpeech || '暂无发言' }}</p>
    </section>

    <section class="history-box">
      <h4>最近发言</h4>
      <ul>
        <li v-for="speech in props.agent.speechHistory" :key="speech">
          {{ speech }}
        </li>
      </ul>
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

.agent-card.dead,
.agent-card.exiled {
  background: #e5e7eb;
  border-color: #f87171;
  color: #4b5563;
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
ul {
  margin: 0;
}

h3 {
  font-size: 1rem;
  color: #111827;
}

h4 {
  margin-bottom: 8px;
  font-size: 0.95rem;
  color: #1f2937;
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

.speech-box,
.history-box {
  padding: 14px;
  border-radius: 14px;
  background: #f8fafc;
}

ul {
  padding-left: 18px;
}

li + li {
  margin-top: 6px;
}
</style>
