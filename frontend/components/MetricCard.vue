<script setup lang="ts">
withDefaults(
  defineProps<{
    label: string
    value: string | number
    icon: string
    tone?: 'default' | 'ok' | 'warning' | 'alert' | 'accent'
    detail?: string
  }>(),
  {
    tone: 'default',
  },
)

const toneClasses = {
  default: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300',
  ok: 'bg-green-50 text-green-700 dark:bg-green-950/50 dark:text-green-300',
  warning: 'bg-amber-50 text-amber-700 dark:bg-amber-950/50 dark:text-amber-300',
  alert: 'bg-red-50 text-red-700 dark:bg-red-950/50 dark:text-red-300',
  accent: 'bg-cyan-50 text-cyan-700 dark:bg-cyan-950/50 dark:text-cyan-300',
} as const
</script>

<template>
  <div class="monitor-panel p-4">
    <div class="flex items-start justify-between gap-4">
      <div>
        <p class="text-xs font-medium text-slate-500 dark:text-slate-400">{{ label }}</p>
        <p class="mt-2 text-2xl font-semibold tabular-nums tracking-tight">{{ value }}</p>
        <p v-if="detail" class="mt-1 text-xs text-slate-500 dark:text-slate-400">{{ detail }}</p>
      </div>
      <div class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg" :class="toneClasses[tone]">
        <UIcon :name="icon" class="h-5 w-5" />
      </div>
    </div>
  </div>
</template>
