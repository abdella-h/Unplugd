<script setup lang="ts">
import type { DeviceState } from '~/types/api'

const props = defineProps<{ state: DeviceState }>()

const colors = {
  ok: 'green',
  warning: 'amber',
  alert: 'red',
} as const

const color = computed(() => colors[props.state])
</script>

<template>
  <UBadge :color="color" variant="subtle">{{ state }}</UBadge>
</template>
