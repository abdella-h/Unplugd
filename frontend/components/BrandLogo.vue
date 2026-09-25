<script setup lang="ts">
withDefaults(
  defineProps<{
    compact?: boolean
    showWordmark?: boolean
  }>(),
  {
    compact: false,
    showWordmark: true,
  },
)
</script>

<template>
  <div class="inline-flex items-center gap-2.5" :class="compact ? 'justify-center' : ''">
    <svg
      viewBox="0 0 32 32"
      class="h-8 w-8 shrink-0"
      :class="compact ? 'h-8 w-8' : 'h-9 w-9'"
      aria-hidden="true"
    >
      <path
        d="M7 5v12.5C7 23.3 10.9 27 16 27s9-3.7 9-9.5V5"
        fill="none"
        stroke="currentColor"
        stroke-width="2.5"
        stroke-linecap="round"
      />
      <path
        d="M7 10.5h6M25 10.5h-6"
        fill="none"
        stroke="currentColor"
        stroke-width="2.5"
        stroke-linecap="round"
      />
      <circle cx="16" cy="22" r="2.5" class="fill-primary-400 dark:fill-primary-300" />
    </svg>
    <span
      v-if="showWordmark && !compact"
      class="text-lg font-semibold tracking-[-0.03em]"
      :class="$attrs.class"
    >
      Unplugd
    </span>
  </div>
</template>
