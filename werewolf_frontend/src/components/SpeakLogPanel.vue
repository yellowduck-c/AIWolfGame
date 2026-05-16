<script setup lang="ts">
import type { SpeakLogEntry } from '../stores/game_store'

const props = defineProps<{
  logs: SpeakLogEntry[]
}>()
</script>

<template>
  <section class="speak-log-panel">
    <header>
      <h2>全局发言流</h2>
      <span>{{ props.logs.length }} 条</span>
    </header>

    <ul>
      <li v-for="log in props.logs" :key="`${log.timestamp}-${log.id}-${log.content}`">
        <strong>{{ log.timestamp }}</strong>
        <span>{{ log.id }} 号 · {{ log.role }}</span>
        <p>{{ log.content }}</p>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.speak-log-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 20px;
  border-radius: 20px;
  background: #ffffff;
  box-shadow: 0 16px 36px rgba(15, 23, 42, 0.12);
}

header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

h2,
p,ul {
  margin: 0;
}

ul {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 560px;
  padding: 0;
  overflow: auto;
  list-style: none;
}

li {
  padding: 14px;
  border-radius: 14px;
  background: #f8fafc;
}

strong {
  display: inline-block;
  margin-right: 8px;
  color: #1d4ed8;
}

span {
  color: #475569;
}

p {
  margin-top: 6px;
  color: #111827;
  line-height: 1.5;
}
</style>
