<script setup lang="ts">
withDefaults(
  defineProps<{
    icon?: string
    title: string
    description?: string
  }>(),
  {
    icon: 'i-heroicons-inbox',
  },
)
</script>

<template>
  <div class="flex min-h-56 flex-col items-center justify-center px-6 py-12 text-center">
    <div class="flex h-12 w-12 items-center justify-center rounded-xl border border-[var(--monitor-border)] bg-[var(--monitor-raised)] text-slate-500 dark:text-slate-300">
      <UIcon :name="icon" class="h-6 w-6" />
    </div>
    <h3 class="mt-4 text-sm font-semibold">{{ title }}</h3>
    <p v-if="description" class="mt-1 max-w-sm text-sm text-slate-500 dark:text-slate-400">
      {{ description }}
    </p>
    <div v-if="$slots.actions" class="mt-5">
      <slot name="actions" />
    </div>
  </div>
</template>
