<script setup lang="ts">
import type { Alert, Device, DeviceState } from '~/types/api'

definePageMeta({ title: 'Overview' })

const auth = useAuth()
const workspace = useWorkspace()
const realtime = useRealtime()
const { apiFetch } = useApi()

const POLL_INTERVAL = 20_000
const devices = ref<Device[]>([])
const openAlerts = ref<Alert[]>([])
const loading = ref(true)
const refreshing = ref(false)
const hasLoaded = ref(false)
const error = ref<string | null>(null)
let pollTimer: ReturnType<typeof setInterval> | undefined
let loadSequence = 0
let disposed = false

interface DatacenterSummary {
  id: number
  name: string
  location: string
  ok: number
  warning: number
  alert: number
  total: number
}

const summaries = computed<DatacenterSummary[]>(() => {
  const byDatacenter = new Map<number, DatacenterSummary>()

  for (const datacenter of workspace.datacenters.value) {
    byDatacenter.set(datacenter.id, {
      id: datacenter.id,
      name: datacenter.name,
      location: datacenter.location,
      ok: 0,
      warning: 0,
      alert: 0,
      total: 0,
    })
  }

  for (const device of devices.value) {
    let summary = byDatacenter.get(device.datacenter_id)
    if (!summary) {
      const datacenter = workspace.datacenters.value.find(
        (candidate) => candidate.id === device.datacenter_id,
      )
      summary = {
        id: device.datacenter_id,
        name: datacenter?.name ?? `Datacenter #${device.datacenter_id}`,
        location: datacenter?.location ?? 'Location unavailable',
        ok: 0,
        warning: 0,
        alert: 0,
        total: 0,
      }
      byDatacenter.set(device.datacenter_id, summary)
    }
    summary[device.state] += 1
    summary.total += 1
  }

  return [...byDatacenter.values()].sort(
    (left, right) =>
      right.alert - left.alert ||
      right.warning - left.warning ||
      right.total - left.total ||
      left.name.localeCompare(right.name),
  )
})

const totals = computed(() => ({
  devices: devices.value.length,
  ok: devices.value.filter((device) => device.state === 'ok').length,
  warning: devices.value.filter((device) => device.state === 'warning').length,
  alert: devices.value.filter((device) => device.state === 'alert').length,
}))

const stateRank: Record<DeviceState, number> = { alert: 0, warning: 1, ok: 2 }
const attentionItems = computed(() => {
  if (auth.isAdmin.value) {
    return [...openAlerts.value]
      .sort(
        (left, right) =>
          stateRank[left.new_state] - stateRank[right.new_state] ||
          new Date(right.occurred_at).getTime() - new Date(left.occurred_at).getTime(),
      )
      .slice(0, 6)
  }
  return devices.value
    .filter((device) => device.state !== 'ok')
    .sort(
      (left, right) =>
        stateRank[left.state] - stateRank[right.state] ||
        new Date(right.updated_at).getTime() - new Date(left.updated_at).getTime(),
    )
    .slice(0, 6)
})

const columns = [
  { key: 'name', label: 'Datacenter' },
  { key: 'location', label: 'Location' },
  { key: 'total', label: 'Devices' },
  { key: 'distribution', label: 'Reported State' },
]

function formatTime(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

async function load(): Promise<boolean> {
  const sequence = ++loadSequence
  error.value = null

  try {
    const [loadedDevices, loadedAlerts] = await Promise.all([
      apiFetch<Device[]>('/api/devices/devices'),
      auth.isAdmin.value
        ? apiFetch<Alert[]>('/api/dashboard/alerts?acknowledged=false')
        : Promise.resolve([]),
    ])
    if (sequence !== loadSequence) return false
    devices.value = loadedDevices
    openAlerts.value = loadedAlerts
    hasLoaded.value = true
    workspace.markFresh()
    return true
  } catch (caught) {
    if (sequence !== loadSequence) return false
    error.value = errorDetail(caught)
    workspace.markStale()
    return false
  }
}

async function refresh() {
  if (loading.value || refreshing.value) return
  if (!hasLoaded.value) loading.value = true
  refreshing.value = true
  try {
    await Promise.all([load(), workspace.refresh()])
  } finally {
    if (!disposed) {
      loading.value = false
      refreshing.value = false
    }
  }
}

watch(realtime.lastEvent, () => {
  void load()
})

watch(workspace.generation, () => {
  loadSequence += 1
  devices.value = []
  openAlerts.value = []
  hasLoaded.value = false
  error.value = null
  loading.value = Boolean(auth.user.value)
  if (auth.user.value) void load()
})

onMounted(async () => {
  await Promise.all([load(), workspace.refresh()])
  if (disposed) return
  loading.value = false
  pollTimer = setInterval(() => void load(), POLL_INTERVAL)
})

onBeforeUnmount(() => {
  disposed = true
  loadSequence += 1
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<template>
  <div class="space-y-6">
    <AppPageHeader
      title="Operational overview"
      description="Current human-reported Device State and Open Alerts across the Datacenters available to you."
    >
      <template #actions>
        <UButton
          icon="i-heroicons-arrow-path"
          color="gray"
          :loading="refreshing"
          :disabled="loading"
          @click="refresh"
        >
          Refresh
        </UButton>
      </template>
    </AppPageHeader>

    <UAlert
      v-if="error && hasLoaded"
      color="amber"
      variant="subtle"
      title="Showing the last successful data"
      :description="error"
    >
      <template #actions>
        <UButton color="amber" variant="soft" size="xs" @click="refresh">Retry</UButton>
      </template>
    </UAlert>

    <div v-if="error && !hasLoaded" class="monitor-panel">
      <AppEmptyState
        icon="i-heroicons-exclamation-triangle"
        title="Overview unavailable"
        :description="error ?? 'The current Device State and Alert context could not be loaded.'"
      >
        <template #actions>
          <UButton color="primary" @click="refresh">Retry overview</UButton>
        </template>
      </AppEmptyState>
    </div>

    <div v-if="loading" class="grid gap-3 sm:grid-cols-2 xl:grid-cols-5" aria-label="Loading overview" role="status" aria-busy="true">
      <span class="sr-only">Loading operational overview</span>
      <div v-for="index in 5" :key="index" class="monitor-panel h-28 p-4">
        <div class="monitor-skeleton h-3 w-24 rounded" />
        <div class="monitor-skeleton mt-4 h-7 w-16 rounded" />
      </div>
      <div class="monitor-panel h-72 sm:col-span-2 xl:col-span-3">
        <div class="monitor-skeleton h-full min-h-64 rounded-lg" />
      </div>
      <div class="monitor-panel h-72 sm:col-span-2 xl:col-span-2">
        <div class="monitor-skeleton h-full min-h-64 rounded-lg" />
      </div>
    </div>

    <template v-else-if="hasLoaded">
      <section id="fleet-kpis" aria-label="Fleet State KPIs">
        <div class="grid grid-cols-2 gap-3 xl:grid-cols-5">
          <MetricCard label="Total Devices" :value="totals.devices" icon="i-heroicons-cpu-chip" />
          <MetricCard label="Reported OK" :value="totals.ok" icon="i-heroicons-check-circle" tone="ok" />
          <MetricCard label="Reported Warning" :value="totals.warning" icon="i-heroicons-exclamation-triangle" tone="warning" />
          <MetricCard label="Reported Alert" :value="totals.alert" icon="i-heroicons-exclamation-octagon" tone="alert" />
          <MetricCard
            v-if="auth.isAdmin.value"
            label="Open Alerts"
            :value="workspace.openAlertCount.value ?? openAlerts.length"
            icon="i-heroicons-bell-alert"
            tone="accent"
            detail="Unacknowledged Alert records"
          />
          <MetricCard
            v-else
            label="Assigned Datacenter"
            :value="workspace.scopeLabel.value"
            icon="i-heroicons-building-office-2"
            tone="accent"
          />
        </div>
      </section>

      <div class="grid gap-5 xl:grid-cols-5">
        <section class="monitor-panel xl:col-span-2" aria-labelledby="attention-heading">
          <div class="flex items-center justify-between border-b border-[var(--monitor-border)] px-5 py-4">
            <div>
              <h2 id="attention-heading" class="text-sm font-semibold">Needs attention</h2>
              <p class="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
                {{ auth.isAdmin.value ? 'Newest and most severe Open Alerts' : 'Devices not reported as ok' }}
              </p>
            </div>
            <UButton
              v-if="auth.isAdmin.value"
              to="/alerts"
              trailing-icon="i-heroicons-arrow-right"
              color="gray"
              variant="ghost"
              size="xs"
            >
              All Alerts
            </UButton>
            <UButton
              v-else
              to="/devices"
              trailing-icon="i-heroicons-arrow-right"
              color="gray"
              variant="ghost"
              size="xs"
            >
              All Devices
            </UButton>
          </div>

          <AppEmptyState
            v-if="attentionItems.length === 0"
            icon="i-heroicons-shield-check"
            :title="auth.isAdmin.value ? 'No Open Alerts' : 'All Devices are reported ok'"
            :description="auth.isAdmin.value ? 'New warning and alert transitions will appear here.' : 'No Device currently needs operator attention.'"
          />

          <ul v-else class="divide-y divide-[var(--monitor-border)]">
            <li v-for="item in attentionItems" :key="`${auth.isAdmin.value ? 'alert' : 'device'}-${item.id}`">
              <NuxtLink
                :to="auth.isAdmin.value ? `/devices/${(item as Alert).device_id}` : `/devices/${item.id}`"
                class="group flex items-center gap-3 px-5 py-3.5 hover:bg-slate-50 dark:hover:bg-[#172033]"
              >
                <StateBadge :state="auth.isAdmin.value ? (item as Alert).new_state : (item as Device).state" />
                <div class="min-w-0 flex-1">
                  <p class="truncate text-sm font-medium">
                    {{ auth.isAdmin.value ? `Device #${(item as Alert).device_id}` : (item as Device).name }}
                  </p>
                  <p class="mt-0.5 truncate text-xs text-slate-500 dark:text-slate-400">
                    <template v-if="auth.isAdmin.value">
                      {{ workspace.datacenterName((item as Alert).datacenter_id) }} · {{ formatTime((item as Alert).occurred_at) }}
                    </template>
                    <template v-else>
                      {{ (item as Device).type }} · Updated {{ formatTime((item as Device).updated_at) }}
                    </template>
                  </p>
                </div>
                <UIcon name="i-heroicons-chevron-right" class="h-4 w-4 text-slate-400 transition-transform group-hover:translate-x-0.5" />
              </NuxtLink>
              <NuxtLink
                v-if="auth.isAdmin.value"
                :to="`/alerts?device_id=${(item as Alert).device_id}&alert_id=${item.id}`"
                class="mt-1 inline-flex text-xs font-medium text-cyan-700 hover:underline dark:text-cyan-300"
              >
                Review Alert #{{ item.id }}
              </NuxtLink>
            </li>
          </ul>
        </section>

        <section class="monitor-panel overflow-hidden xl:col-span-3" aria-labelledby="datacenter-health-heading">
          <div class="flex items-center justify-between border-b border-[var(--monitor-border)] px-5 py-4">
            <div>
              <h2 id="datacenter-health-heading" class="text-sm font-semibold">Datacenter health</h2>
              <p class="mt-0.5 text-xs text-slate-500 dark:text-slate-400">Current reported State distribution</p>
            </div>
            <span class="text-xs text-slate-500 dark:text-slate-400">{{ summaries.length }} visible</span>
          </div>

          <AppEmptyState
            v-if="summaries.length === 0"
            icon="i-heroicons-building-office-2"
            :title="workspace.datacentersLoaded.value ? 'No Datacenters in scope' : 'Datacenter scope unavailable'"
            :description="workspace.datacentersLoaded.value ? 'Datacenter metadata will appear when an authorized scope is available.' : 'Datacenter metadata could not be loaded. Retry to restore scope context.'"
          >
            <template v-if="!workspace.datacentersLoaded.value" #actions>
              <UButton color="primary" @click="refresh">Retry scope</UButton>
            </template>
          </AppEmptyState>

          <template v-else>
            <div class="monitor-table hidden border-0 sm:block">
              <UTable :rows="summaries" :columns="columns">
                <template #name-data="{ row }">
                  <p class="font-semibold text-slate-900 dark:text-white">{{ row.name }}</p>
                </template>
                <template #location-data="{ row }">{{ row.location }}</template>
                <template #total-data="{ row }">
                  <span class="font-semibold tabular-nums text-slate-900 dark:text-white">{{ row.total }}</span>
                </template>
                <template #distribution-data="{ row }">
                  <StateBar :ok="row.ok" :warning="row.warning" :alert="row.alert" />
                </template>
              </UTable>
            </div>
            <ul class="divide-y divide-[var(--monitor-border)] sm:hidden">
              <li v-for="summary in summaries" :key="summary.id" class="space-y-3 p-4">
                <div class="flex items-start justify-between gap-3">
                  <div>
                    <p class="text-sm font-semibold">{{ summary.name }}</p>
                    <p class="mt-0.5 text-xs text-slate-500 dark:text-slate-400">{{ summary.location }}</p>
                  </div>
                  <span class="text-sm font-semibold tabular-nums">{{ summary.total }} Devices</span>
                </div>
                <StateBar :ok="summary.ok" :warning="summary.warning" :alert="summary.alert" />
              </li>
            </ul>
          </template>
        </section>
      </div>
    </template>
  </div>
</template>
