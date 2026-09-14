<script setup lang="ts">
const auth = useAuth()

const links = computed(() => {
  const items = [
    { label: 'Devices', to: '/devices' },
  ]
  if (auth.isAdmin.value) {
    items.push({ label: 'Alerts', to: '/alerts' })
  }
  if (auth.isGlobalAdmin.value) {
    items.push({ label: 'Datacenters', to: '/datacenters' })
  }
  return items
})
</script>

<template>
  <header
    class="flex items-center justify-between border-b border-gray-200 dark:border-gray-800 px-4 py-3"
  >
    <div class="flex items-center gap-6">
      <NuxtLink to="/" class="font-bold">Unplugd</NuxtLink>
      <nav class="flex gap-4">
        <NuxtLink
          v-for="link in links"
          :key="link.to"
          :to="link.to"
          class="text-sm text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white"
          active-class="font-semibold text-primary-600 dark:text-primary-400"
        >
          {{ link.label }}
        </NuxtLink>
      </nav>
    </div>
    <div class="flex items-center gap-3">
      <UBadge color="gray" variant="subtle">
        {{ auth.user.value?.username }} · {{ auth.user.value?.role }}
      </UBadge>
      <UButton size="xs" color="gray" variant="ghost" @click="auth.logout()">
        Log out
      </UButton>
    </div>
  </header>
</template>
