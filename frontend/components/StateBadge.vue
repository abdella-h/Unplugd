<script setup lang="ts">
import type { DeviceState } from '~/types/api'

const props = defineProps<{ state: DeviceState }>()

const presentation = {
  ok: { color: 'green', icon: 'i-heroicons-check-circle', label: 'OK' },
  warning: { color: 'amber', icon: 'i-heroicons-exclamation-triangle', label: 'Warning' },
  alert: { color: 'red', icon: 'i-heroicons-exclamation-octagon', label: 'Alert' },
} as const

const current = computed(() => presentation[props.state])
</script>

<template>
  <UBadge
    :color="current.color"
    variant="subtle"
    :icon="current.icon"
    class="gap-1 font-semibold capitalize"
  >
    {{ current.label }}
  </UBadge>
</template>
