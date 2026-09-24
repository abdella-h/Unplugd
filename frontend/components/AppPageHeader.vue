<script setup lang="ts">
defineProps<{
  title: string
  description?: string
}>()
</script>

<template>
  <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
    <div>
      <p class="text-xs font-semibold uppercase tracking-[0.16em] text-primary-700 dark:text-primary-300">
        Unplugd operations
      </p>
      <h2 class="mt-1 text-2xl font-semibold tracking-tight">{{ title }}</h2>
      <p v-if="description" class="mt-1 max-w-3xl text-sm text-slate-500 dark:text-slate-400">
        {{ description }}
      </p>
    </div>
    <div v-if="$slots.actions" class="flex shrink-0 flex-wrap items-center gap-2">
      <slot name="actions" />
    </div>
  </div>
</template>
