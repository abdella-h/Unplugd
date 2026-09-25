<script setup lang="ts">
import type { StreamEvent } from '~/types/api'

const auth = useAuth()
const workspace = useWorkspace()
const profile = useUserProfile()
const realtime = useRealtime()
const toast = useToast()
const mobileNavigationOpen = useState<boolean>('shell:mobile-navigation-open', () => false)

onMounted(() => {
  void profile.load()
  void workspace.refresh()
  void realtime.connect()
})

const authIdentity = computed(() => {
  const user = auth.user.value
  return user ? `${user.username}|${user.role}|${user.dcId ?? ''}` : ''
})

watch(
  authIdentity,
  (identity, previousIdentity) => {
    const identityChanged = Boolean(previousIdentity && identity !== previousIdentity)
    if (identityChanged || !identity) {
      profile.reset()
      workspace.reset()
      realtime.clear()
    }
    if (identity) {
      void profile.load()
      void workspace.refresh()
      void realtime.connect()
    }
  },
  { flush: 'sync' },
)

watch(realtime.lastEvent, (event) => {
  if (!event) return
  if (event.type === 'device_status_changed') {
    if (event.new_state === 'alert') {
      toast.add({
        title: `Device #${event.device_id} requires attention`,
        description: `Reported State changed from ${event.old_state} to ${event.new_state}.`,
        color: 'red',
      })
    } else if (event.new_state === 'ok') {
      toast.add({
        title: `Device #${event.device_id} recovered`,
        description: 'The reported State is now ok.',
        color: 'green',
      })
    }
  }
})

onBeforeUnmount(() => realtime.disconnect())
</script>

<template>
  <div class="min-h-screen bg-[var(--monitor-canvas)] text-[var(--monitor-text)]">
    <a
      href="#main-content"
      class="sr-only fixed left-3 top-3 z-[100] rounded-md bg-primary-500 px-3 py-2 text-sm font-semibold text-primary-950 focus:not-sr-only"
    >
      Skip to content
    </a>
    <AppSidebar />
    <div
      class="min-h-screen transition-[padding] duration-200"
      :class="workspace.sidebarCollapsed.value ? 'lg:pl-[72px]' : 'lg:pl-60'"
    >
      <AppTopbar @open-navigation="mobileNavigationOpen = true" />
      <main id="main-content" class="mx-auto w-full max-w-[1800px] px-4 py-5 sm:px-6 sm:py-6 lg:px-8">
        <slot />
      </main>
    </div>
  </div>
</template>
