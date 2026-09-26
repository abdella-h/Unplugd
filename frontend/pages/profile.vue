<script setup lang="ts">
definePageMeta({ title: 'Profile' })

const workspace = useWorkspace()
const profile = useUserProfile()

const currentProfile = computed(() => profile.profile.value)
const displayName = profile.displayName
const roleLabel = profile.roleLabel
const scopeLabel = computed(() => {
  if (profile.isGlobalAdmin.value) return 'All datacenters'
  const datacenterId = profile.datacenterId.value
  if (datacenterId == null) return 'Datacenter unavailable'
  if (!workspace.datacentersLoaded.value) {
    return workspace.stale.value ? 'Datacenter unavailable' : 'Loading scope…'
  }
  return workspace.datacenters.value.find((datacenter) => datacenter.id === datacenterId)?.name ?? 'Datacenter unavailable'
})
const isInitialLoading = computed(() => !currentProfile.value && !profile.error.value)

function formatDate(value: string | null): string {
  if (!value) return 'Never'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'Unavailable'
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date)
}

onMounted(() => {
  void profile.load()
})
</script>

<template>
  <div class="mx-auto max-w-4xl space-y-5">
    <AppPageHeader
      title="Profile"
      description="Review your account identity and access context."
    >
      <template #actions>
        <UButton
          icon="i-heroicons-arrow-path"
          color="gray"
          variant="outline"
          :loading="profile.loading.value"
          @click="profile.load(true)"
        >
          Refresh
        </UButton>
      </template>
    </AppPageHeader>

    <UAlert
      v-if="profile.error.value && currentProfile"
      color="amber"
      variant="subtle"
      title="Showing the last successful profile"
      :description="profile.error.value"
    >
      <template #actions>
        <UButton size="xs" color="amber" variant="soft" @click="profile.load(true)">Retry</UButton>
      </template>
    </UAlert>

    <div
      v-if="isInitialLoading"
      class="monitor-panel p-5"
      aria-label="Loading profile"
      role="status"
      aria-busy="true"
    >
      <span class="sr-only">Loading profile</span>
      <div class="flex items-center gap-4">
        <div class="monitor-skeleton h-14 w-14 rounded-full" />
        <div class="flex-1 space-y-3">
          <div class="monitor-skeleton h-5 w-48 rounded" />
          <div class="monitor-skeleton h-4 w-32 rounded" />
        </div>
      </div>
      <div class="mt-8 grid gap-4 sm:grid-cols-2">
        <div v-for="index in 6" :key="index" class="monitor-skeleton h-16 rounded-lg" />
      </div>
    </div>

    <div v-else-if="profile.error.value && !currentProfile" class="monitor-panel">
      <AppEmptyState
        icon="i-heroicons-exclamation-triangle"
        title="Profile unavailable"
        :description="profile.error.value"
      >
        <template #actions>
          <UButton color="primary" @click="profile.load(true)">Retry profile</UButton>
        </template>
      </AppEmptyState>
    </div>

    <template v-else-if="currentProfile">
      <section class="monitor-panel overflow-hidden" aria-labelledby="profile-identity-heading">
        <div class="flex flex-col gap-4 border-b border-[var(--monitor-border)] p-5 sm:flex-row sm:items-center">
          <UAvatar :alt="displayName" :text="profile.initials.value" size="xl" />
          <div class="min-w-0 flex-1">
            <div class="flex flex-wrap items-center gap-3">
              <h2 id="profile-identity-heading" class="text-xl font-semibold">{{ displayName }}</h2>
              <UBadge color="gray" variant="subtle">
                {{ currentProfile.is_active ? 'Active' : 'Inactive' }}
              </UBadge>
            </div>
            <p class="mt-1 text-sm text-slate-500 dark:text-slate-400">@{{ currentProfile.username }}</p>
          </div>
        </div>

        <dl class="grid gap-px bg-[var(--monitor-border)] sm:grid-cols-2">
          <div class="bg-[var(--monitor-surface)] p-5">
            <dt class="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500 dark:text-slate-400">First name</dt>
            <dd class="mt-2 text-sm font-medium">{{ currentProfile.first_name || 'Not provided' }}</dd>
          </div>
          <div class="bg-[var(--monitor-surface)] p-5">
            <dt class="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500 dark:text-slate-400">Last name</dt>
            <dd class="mt-2 text-sm font-medium">{{ currentProfile.last_name || 'Not provided' }}</dd>
          </div>
          <div class="bg-[var(--monitor-surface)] p-5">
            <dt class="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500 dark:text-slate-400">Email</dt>
            <dd class="mt-2 break-all text-sm font-medium">{{ currentProfile.email }}</dd>
          </div>
          <div class="bg-[var(--monitor-surface)] p-5">
            <dt class="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500 dark:text-slate-400">Role</dt>
            <dd class="mt-2 text-sm font-medium">{{ roleLabel }}</dd>
          </div>
          <div class="bg-[var(--monitor-surface)] p-5">
            <dt class="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500 dark:text-slate-400">Datacenter scope</dt>
            <dd class="mt-2 text-sm font-medium">{{ scopeLabel }}</dd>
          </div>
          <div class="bg-[var(--monitor-surface)] p-5">
            <dt class="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500 dark:text-slate-400">Last login</dt>
            <dd class="mt-2 text-sm font-medium">{{ formatDate(currentProfile.last_login_at) }}</dd>
          </div>
        </dl>
      </section>
    </template>
  </div>
</template>
