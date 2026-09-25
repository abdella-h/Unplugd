<script setup lang="ts">
const emit = defineEmits<{
  openNavigation: []
}>()

const auth = useAuth()
const route = useRoute()
const colorMode = useColorMode()
const workspace = useWorkspace()
const realtime = useRealtime()
const mobileNavigationOpen = useState<boolean>('shell:mobile-navigation-open', () => false)
const userMenuOpen = ref(false)

const title = computed(() => String(route.meta.title ?? 'Overview'))
const isDark = computed(() => colorMode.value === 'dark')
const initials = computed(() => auth.user.value?.username?.slice(0, 2).toUpperCase() ?? 'U')
const clock = ref(Date.now())
let freshnessTimer: ReturnType<typeof setInterval> | undefined

const freshnessLabel = computed(() => {
  if (!workspace.lastUpdatedAt.value) return 'Not fetched yet'
  const elapsed = Math.max(0, clock.value - workspace.lastUpdatedAt.value)
  if (elapsed < 60_000) return 'Just now'
  const minutes = Math.floor(elapsed / 60_000)
  if (minutes < 60) return `${minutes}m ago`
  return `${Math.floor(minutes / 60)}h ago`
})

const freshnessText = computed(() => {
  if (!workspace.lastUpdatedAt.value) return 'Not fetched yet'
  return workspace.stale.value ? `Stale · fetched ${freshnessLabel.value}` : `Fetched ${freshnessLabel.value}`
})

const realtimeLabel = computed(() => {
  const labels = {
    idle: 'Realtime channel idle',
    connecting: 'Realtime channel connecting',
    connected: 'Realtime channel connected',
    reconnecting: 'Realtime channel reconnecting',
    offline: 'Realtime channel offline',
  }
  return labels[realtime.status.value]
})

const realtimeColor = computed(() => {
  if (realtime.status.value === 'connected') return 'bg-emerald-400'
  if (realtime.status.value === 'connecting' || realtime.status.value === 'reconnecting') return 'bg-amber-400'
  return 'bg-slate-400'
})

const userItems = computed(() => [
  [
    { label: auth.user.value?.username ?? 'User', disabled: true },
    { label: workspace.roleLabel.value, disabled: true },
    { label: workspace.scopeLabel.value, disabled: true },
    { label: 'Log out', icon: 'i-heroicons-arrow-right-start-on-rectangle', click: () => auth.logout() },
  ],
])

onMounted(() => {
  freshnessTimer = setInterval(() => {
    clock.value = Date.now()
  }, 30_000)
})

onBeforeUnmount(() => {
  if (freshnessTimer) clearInterval(freshnessTimer)
})

function toggleTheme() {
  colorMode.preference = isDark.value ? 'light' : 'dark'
}
</script>

<template>
  <header class="sticky top-0 z-30 flex h-16 items-center border-b border-[var(--monitor-border)] bg-[color:var(--monitor-surface)]/95 px-4 backdrop-blur sm:px-6 lg:px-8">
    <UButton
      icon="i-heroicons-bars-3"
      color="gray"
      variant="ghost"
      square
      class="mr-2 lg:hidden"
      aria-label="Open navigation"
      aria-controls="primary-navigation"
      :aria-expanded="mobileNavigationOpen"
      @click="emit('openNavigation')"
    />
    <div class="min-w-0">
      <h1 class="truncate text-base font-semibold tracking-tight">{{ title }}</h1>
      <div class="mt-0.5 hidden items-center gap-2 text-xs text-slate-500 dark:text-slate-400 md:flex">
        <UIcon name="i-heroicons-building-office-2" class="h-3.5 w-3.5" />
        <span class="truncate">{{ workspace.scopeLabel.value }}</span>
      </div>
      <div class="mt-0.5 flex min-w-0 items-center gap-1.5 text-[11px] text-slate-500 dark:text-slate-400 md:hidden">
        <span class="truncate">{{ freshnessText }}</span>
        <span aria-hidden="true">·</span>
        <span class="truncate">{{ workspace.scopeLabel.value }}</span>
        <span v-if="auth.isAdmin.value" class="truncate">· {{ realtimeLabel }}</span>
      </div>
    </div>

    <div class="ml-auto flex items-center gap-1.5 sm:gap-3">
      <div class="hidden items-center gap-2 text-xs text-slate-500 dark:text-slate-400 md:flex">
        <span
          class="h-2 w-2 rounded-full"
          :class="[realtimeColor, workspace.stale.value && workspace.lastUpdatedAt.value ? 'bg-amber-400' : '']"
          aria-hidden="true"
        />
        <span>{{ freshnessText }}</span>
      </div>
      <div
        v-if="auth.isAdmin.value"
        class="hidden items-center gap-2 text-xs text-slate-500 dark:text-slate-400 md:flex"
        :title="realtimeLabel"
      >
        <span class="h-2 w-2 rounded-full" :class="realtimeColor" aria-hidden="true" />
        <span>{{ realtimeLabel }}</span>
      </div>
      <AppActivityMenu v-if="auth.isAdmin.value" />
      <UButton
        :icon="isDark ? 'i-heroicons-sun' : 'i-heroicons-moon'"
        color="gray"
        variant="ghost"
        square
        :aria-label="isDark ? 'Use light theme' : 'Use dark theme'"
        @click="toggleTheme"
      />
      <UDropdown v-model:open="userMenuOpen" :items="userItems" placement="bottom-end">
        <UButton
          color="gray"
          variant="ghost"
          class="gap-2 px-1.5 sm:px-2"
          aria-label="Open user menu"
          aria-haspopup="true"
          :aria-expanded="userMenuOpen"
        >
          <UAvatar :alt="auth.user.value?.username ?? 'User'" :text="initials" size="sm" />
          <span class="hidden max-w-28 truncate text-sm font-medium sm:inline">{{ auth.user.value?.username }}</span>
          <UIcon name="i-heroicons-chevron-down" class="hidden h-3.5 w-3.5 sm:block" />
        </UButton>
      </UDropdown>
    </div>
  </header>
</template>
