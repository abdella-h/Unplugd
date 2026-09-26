<script setup lang="ts">
const auth = useAuth()
const workspace = useWorkspace()
const profile = useUserProfile()
const mobileOpen = useState<boolean>('shell:mobile-navigation-open', () => false)
const isDesktop = ref(false)
const sidebarElement = ref<HTMLElement | null>(null)
let desktopQuery: MediaQueryList | undefined
let updateDesktopState: ((event?: MediaQueryListEvent) => void) | undefined

interface NavigationItem {
  label: string
  to: string
  icon: string
  exact?: boolean
  count?: number | null
}

const groups = computed(() => {
  const monitor: NavigationItem[] = [
    { label: 'Overview', to: '/', icon: 'i-heroicons-squares-2x2', exact: true },
  ]
  const infrastructure: NavigationItem[] = [
    { label: 'Devices', to: '/devices', icon: 'i-heroicons-cpu-chip' },
  ]

  if (auth.isAdmin.value) {
    monitor.push({
      label: 'Alerts',
      to: '/alerts',
      icon: 'i-heroicons-bell-alert',
      count: workspace.openAlertCount.value,
    })
  }
  if (auth.isGlobalAdmin.value) {
    infrastructure.push({
      label: 'Datacenters',
      to: '/datacenters',
      icon: 'i-heroicons-building-office-2',
    })
  }

  return [
    { label: 'Monitor', items: monitor },
    { label: 'Infrastructure', items: infrastructure },
  ].filter((group) => group.items.length > 0)
})

onMounted(() => {
  workspace.sidebarCollapsed.value = window.localStorage.getItem('unplugd:sidebar-collapsed') === 'true'
  desktopQuery = window.matchMedia('(min-width: 1024px)')
  updateDesktopState = (event?: MediaQueryListEvent) => {
    isDesktop.value = event?.matches ?? desktopQuery?.matches ?? false
  }
  updateDesktopState()
  desktopQuery.addEventListener('change', updateDesktopState)
})

onBeforeUnmount(() => {
  if (desktopQuery && updateDesktopState) {
    desktopQuery.removeEventListener('change', updateDesktopState)
  }
})

watch(mobileOpen, async (open) => {
  await nextTick()
  if (open) {
    sidebarElement.value?.querySelector<HTMLElement>('a, button')?.focus()
  } else {
    document.querySelector<HTMLElement>('[aria-label="Open navigation"]')?.focus()
  }
})

watch(workspace.sidebarCollapsed, (collapsed) => {
  if (import.meta.client) window.localStorage.setItem('unplugd:sidebar-collapsed', String(collapsed))
})

function toggleCollapsed() {
  workspace.sidebarCollapsed.value = !workspace.sidebarCollapsed.value
}

function closeMobile() {
  mobileOpen.value = false
}

function handleNavigationKeydown(event: KeyboardEvent) {
  if (!mobileOpen.value || isDesktop.value) return
  if (event.key === 'Escape') {
    event.preventDefault()
    closeMobile()
    return
  }
  if (event.key !== 'Tab' || !sidebarElement.value) return
  const focusable = [...sidebarElement.value.querySelectorAll<HTMLElement>(
    'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
  )].filter((element) => element.getClientRects().length > 0)
  if (focusable.length === 0) return
  const first = focusable[0]
  const last = focusable[focusable.length - 1]
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault()
    last.focus()
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault()
    first.focus()
  }
}
</script>

<template>
  <div>
    <Transition
      enter="transition-opacity duration-150"
      enter-from="opacity-0"
      enter-to="opacity-100"
      leave="transition-opacity duration-150"
      leave-from="opacity-100"
      leave-to="opacity-0"
    >
      <button
        v-if="mobileOpen"
        class="fixed inset-0 z-40 bg-slate-950/60 backdrop-blur-sm lg:hidden"
        aria-label="Close navigation"
        @click="closeMobile"
      />
    </Transition>
    <aside
      id="primary-navigation"
      ref="sidebarElement"
      class="fixed inset-y-0 left-0 z-50 flex border-r border-[var(--monitor-border)] bg-[var(--monitor-surface)] transition-[width,transform] duration-200 lg:translate-x-0"
      :class="[
        mobileOpen ? 'translate-x-0' : '-translate-x-full',
        workspace.sidebarCollapsed.value ? 'w-72 lg:w-[72px]' : 'w-72 lg:w-60',
      ]"
      :inert="!isDesktop && !mobileOpen"
      :aria-hidden="!isDesktop && !mobileOpen ? 'true' : undefined"
      aria-label="Primary navigation"
      @keydown="handleNavigationKeydown"
    >
      <div class="flex min-w-0 flex-1 flex-col">
        <div class="flex h-16 items-center border-b border-[var(--monitor-border)] px-4">
          <BrandLogo
            :compact="workspace.sidebarCollapsed.value"
            class="text-slate-900 dark:text-white"
          />
          <button
            class="ml-auto inline-flex h-9 w-9 items-center justify-center rounded-md text-slate-500 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-white lg:hidden"
            aria-label="Close navigation"
            @click="closeMobile"
          >
            <UIcon name="i-heroicons-x-mark" class="h-5 w-5" />
          </button>
        </div>

        <nav class="flex-1 space-y-6 overflow-y-auto px-3 py-5">
          <section v-for="group in groups" :key="group.label">
            <p
              v-if="!workspace.sidebarCollapsed.value"
               class="mb-2 px-3 text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500 dark:text-slate-400"
            >
              {{ group.label }}
            </p>
            <div v-else class="mx-3 mb-3 border-t border-[var(--monitor-border)]" />
            <div class="space-y-1">
              <UTooltip
                v-for="item in group.items"
                :key="item.to"
                :text="item.label"
                :disabled="!workspace.sidebarCollapsed.value"
                placement="right"
              >
                <NuxtLink
                  :to="item.to"
                  class="group relative flex h-10 items-center gap-3 rounded-md px-3 text-sm font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-950 dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:text-white"
                  active-class="bg-cyan-50 text-cyan-800 dark:bg-cyan-950/50 dark:text-cyan-200"
                  :exact-active-class="item.exact ? 'bg-cyan-50 text-cyan-800 dark:bg-cyan-950/50 dark:text-cyan-200' : ''"
                  :aria-label="item.count !== null && item.count !== undefined ? `${item.label}, ${item.count} Open Alerts` : item.label"
                  :title="workspace.sidebarCollapsed.value ? item.label : undefined"
                  @click="closeMobile"
                >
                  <span
                    v-if="workspace.sidebarCollapsed.value"
                    class="absolute inset-y-2 left-0 w-0.5 rounded-full bg-transparent group-[.router-link-active]:bg-primary-500"
                  />
                  <UIcon :name="item.icon" class="h-5 w-5 shrink-0" />
                  <span v-if="!workspace.sidebarCollapsed.value" class="truncate">{{ item.label }}</span>
                  <span
                    v-if="!workspace.sidebarCollapsed.value && item.count !== null && item.count !== undefined"
                    class="ml-auto rounded-full bg-red-100 px-2 py-0.5 text-[11px] font-semibold tabular-nums text-red-700 dark:bg-red-950/60 dark:text-red-300"
                  >
                    {{ item.count > 99 ? '99+' : item.count }}
                  </span>
                  <span
                    v-else-if="workspace.sidebarCollapsed.value && item.count"
                    class="absolute right-2 top-1 h-2 w-2 rounded-full bg-red-500 ring-2 ring-[var(--monitor-surface)]"
                  />
                </NuxtLink>
              </UTooltip>
            </div>
          </section>
        </nav>

        <div class="border-t border-[var(--monitor-border)] p-3">
          <div class="flex items-center gap-2 rounded-md px-2 py-2">
            <UTooltip
              text="Profile"
              :disabled="!workspace.sidebarCollapsed.value"
              placement="right"
            >
              <NuxtLink
                to="/profile"
                class="flex min-w-0 flex-1 items-center gap-3 rounded-md p-1 hover:bg-slate-100 dark:hover:bg-slate-800"
                :aria-label="`Open profile for ${profile.displayName.value || 'user'}`"
                @click="closeMobile"
              >
                <UAvatar
                  :alt="profile.displayName.value || 'User'"
                  :text="profile.initials.value"
                  size="sm"
                />
                <div v-if="!workspace.sidebarCollapsed.value" class="min-w-0">
                  <p class="truncate text-sm font-semibold">{{ profile.displayName.value || auth.user.value?.username }}</p>
                  <p class="truncate text-xs text-slate-500 dark:text-slate-400">{{ profile.roleLabel.value }}</p>
                </div>
              </NuxtLink>
            </UTooltip>
            <UButton
              v-if="!workspace.sidebarCollapsed.value"
              icon="i-heroicons-arrow-right-start-on-rectangle"
              color="gray"
              variant="ghost"
              size="xs"
              square
              :aria-label="`Log out ${profile.displayName.value || auth.user.value?.username || 'user'}`"
              @click="auth.logout()"
            />
          </div>
        </div>
      </div>
      <button
        class="absolute -right-3 top-20 hidden h-6 w-6 items-center justify-center rounded-full border border-[var(--monitor-border)] bg-[var(--monitor-surface)] text-slate-500 shadow-sm hover:text-cyan-600 lg:flex"
        :aria-label="workspace.sidebarCollapsed.value ? 'Expand navigation' : 'Collapse navigation'"
        @click="toggleCollapsed"
      >
        <UIcon
          :name="workspace.sidebarCollapsed.value ? 'i-heroicons-chevron-right' : 'i-heroicons-chevron-left'"
          class="h-3.5 w-3.5"
        />
      </button>
    </aside>
  </div>
</template>
