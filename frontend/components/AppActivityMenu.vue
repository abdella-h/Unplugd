<script setup lang="ts">
const realtime = useRealtime()
const activityMenuOpen = ref(false)

const activityItems = computed(() => {
  if (realtime.events.value.length === 0) return []
  return [
    realtime.events.value.slice(0, 8).map((event) => {
      if (event.type === 'device_status_changed') {
        const label =
          event.new_state === 'ok'
            ? `Device #${event.device_id} recovered to ok`
            : `Device #${event.device_id}: ${event.old_state} → ${event.new_state}`
        return {
          label,
          icon: event.new_state === 'ok' ? 'i-heroicons-check-circle' : 'i-heroicons-bell-alert',
          click: () => navigateTo(`/devices/${event.device_id}`),
        }
      }
      return {
        label: `Alert #${event.alert_id} acknowledged`,
        icon: 'i-heroicons-check-badge',
        click: () => navigateTo(`/alerts?tab=acknowledged&alert_id=${event.alert_id}`),
      }
    }),
  ]
})
</script>

<template>
  <UDropdown v-model:open="activityMenuOpen" :items="activityItems" placement="bottom-end">
    <UButton
      color="gray"
      variant="ghost"
      square
      aria-label="Open activity feed"
      aria-haspopup="true"
      :aria-expanded="activityMenuOpen"
      class="relative"
    >
      <UIcon name="i-heroicons-bell" class="h-5 w-5" />
      <span
        v-if="realtime.events.value.length"
        class="absolute right-1 top-1 h-2 w-2 rounded-full bg-cyan-400 ring-2 ring-[var(--monitor-surface)]"
      />
    </UButton>
  </UDropdown>
</template>
