<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    ok: number
    warning: number
    alert: number
    showLegend?: boolean
  }>(),
  {
    showLegend: true,
  },
)

const total = computed(() => props.ok + props.warning + props.alert)
const segments = computed(() =>
  [
    { state: 'ok' as const, value: props.ok, class: 'bg-green-500' },
    { state: 'warning' as const, value: props.warning, class: 'bg-amber-500' },
    { state: 'alert' as const, value: props.alert, class: 'bg-red-500' },
  ].filter((segment) => segment.value > 0),
)
</script>

<template>
  <div>
    <div
      class="flex h-2 w-full overflow-hidden rounded-full bg-slate-200 dark:bg-slate-800"
      role="img"
      :aria-label="`${ok} ok, ${warning} warning, ${alert} alert`"
    >
      <span
        v-for="segment in segments"
        :key="segment.state"
        :class="segment.class"
        :style="{ width: `${(segment.value / total) * 100}%` }"
      />
    </div>
    <div v-if="showLegend" class="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-slate-500 dark:text-slate-400">
      <span class="flex items-center gap-1.5"><UIcon name="i-heroicons-check-circle" class="h-3.5 w-3.5 text-green-700 dark:text-green-300" /> {{ ok }} ok</span>
      <span class="flex items-center gap-1.5"><UIcon name="i-heroicons-exclamation-triangle" class="h-3.5 w-3.5 text-amber-700 dark:text-amber-300" /> {{ warning }} warning</span>
      <span class="flex items-center gap-1.5"><UIcon name="i-heroicons-exclamation-octagon" class="h-3.5 w-3.5 text-red-700 dark:text-red-300" /> {{ alert }} alert</span>
    </div>
  </div>
</template>
