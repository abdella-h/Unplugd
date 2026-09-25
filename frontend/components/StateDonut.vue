<script setup lang="ts">
const props = defineProps<{ ok: number; warning: number; alert: number }>()

const total = computed(() => props.ok + props.warning + props.alert)

// Segments as percentages of a 100-unit circumference (r = 15.9155).
// stroke-dashoffset accumulates so segments tile the ring.
const segments = computed(() => {
  if (total.value === 0) return []
  const parts = [
    { value: props.ok, color: '#22c55e' },
    { value: props.warning, color: '#f59e0b' },
    { value: props.alert, color: '#ef4444' },
  ]
  let offset = 25 // start at 12 o'clock (dash pattern starts at 3 o'clock)
  return parts
    .filter((p) => p.value > 0)
    .map((p) => {
      const pct = (p.value / total.value) * 100
      const seg = { ...p, pct, offset }
      offset -= pct
      return seg
    })
})
</script>

<template>
  <svg viewBox="0 0 42 42" class="h-20 w-20" role="img" :aria-label="`${ok} ok, ${warning} warning, ${alert} alert`">
    <circle
      cx="21"
      cy="21"
      r="15.9155"
      fill="transparent"
      stroke-width="6"
      class="stroke-gray-200 dark:stroke-gray-800"
    />
    <circle
      v-for="seg in segments"
      :key="seg.color"
      cx="21"
      cy="21"
      r="15.9155"
      fill="transparent"
      :stroke="seg.color"
      stroke-width="6"
      :stroke-dasharray="`${seg.pct} ${100 - seg.pct}`"
      :stroke-dashoffset="seg.offset"
    />
    <text
      x="21"
      y="21"
      text-anchor="middle"
      dominant-baseline="central"
      class="fill-gray-900 dark:fill-white text-[9px] font-semibold"
    >
      {{ total }}
    </text>
  </svg>
</template>
