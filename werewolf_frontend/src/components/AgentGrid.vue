<script setup lang="ts">
import { computed } from 'vue'

import type { Agent } from '../stores/game_store'
import AgentCard from './AgentCard.vue'

const props = defineProps<{
  agents: Agent[]
}>()

const gridClass = computed(() => {
  const count = props.agents.length

  if (count >= 7 && count <= 12) {
    return `two-rows columns-${Math.ceil(count / 2)}`
  }

  if (count === 6) {
    return 'single-row columns-6'
  }

  return 'fallback-grid'
})
</script>

<template>
  <section class="agent-grid" :class="gridClass">
    <AgentCard v-for="agent in props.agents" :key="`${agent.id}-${agent.currentSpeech}-${agent.status}`" :agent="agent" />
  </section>
</template>

<style scoped>
.agent-grid {
  display: grid;
  gap: 18px;
  align-items: stretch;
}

.agent-grid.single-row {
  grid-auto-flow: column;
  grid-auto-columns: minmax(0, 1fr);
}

.agent-grid.two-rows {
  grid-template-rows: repeat(2, minmax(0, 1fr));
  grid-auto-flow: row;
}

.agent-grid.columns-4,
.agent-grid.columns-5,
.agent-grid.columns-6 {
  grid-template-columns: repeat(var(--column-count, 1), minmax(0, 1fr));
}

.agent-grid.columns-4 {
  --column-count: 4;
}

.agent-grid.columns-5 {
  --column-count: 5;
}

.agent-grid.columns-6 {
  --column-count: 6;
}

.agent-grid.fallback-grid {
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
}

@media (max-width: 1600px) {
  .agent-grid.single-row {
    grid-auto-flow: row;
  }

  .agent-grid.two-rows {
    grid-auto-flow: row;
    grid-template-rows: none;
  }

  .agent-grid.columns-4,
  .agent-grid.columns-5,
  .agent-grid.columns-6 {
    grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  }
}

@media (max-width: 960px) {
  .agent-grid.columns-4,
  .agent-grid.columns-5,
  .agent-grid.columns-6,
  .agent-grid.fallback-grid {
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  }
}
</style>
