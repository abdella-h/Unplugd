<script setup lang="ts">
import type { Alert, Datacenter, Device } from '~/types/api'

// Overview: root fleet-health summary (global admin sees all datacenters,
// scoped users only their own — enforced by the backend per ADR-0002).
const auth = useAuth()
const { apiFetch } = useApi()

const POLL_MS = 20000

const devices = ref<Device[]>([])
const datacenters = ref<Datacenter[]>([])
const openAlertCount = ref<number | null>(null)
const loading = ref(true)
const refreshing = ref(false)
const error = ref<string | null>(null)
let pollTimer: ReturnType<typeof setInterval> | undefined
let loadPending = false

const dcName = (id: number) =>
  datacenters.value.find((d) => d.id === id)?.name ?? `#${id}`

interface DcSummary {
  id: number
  name: string
  ok: number
  warning: number
  alert: number
  total: number
}

const summaries = computed<DcSummary[]>(() => {
  const byDc = new Map<number, DcSummary>()
  for (const device of devices.value) {
    let summary = byDc.get(device.datacenter_id)
    if (!summary) {
      summary = {
        id: device.datacenter_id,
        name: dcName(device.datacenter_id),
        ok: 0,
        warning: 0,
        alert: 0,
        total: 0,
      }
      byDc.set(device.datacenter_id, summary)
    }
    summary[device.state] += 1
    summary.total += 1
  }
  // Worst-first so troubled sites read first.
  return [...byDc.values()].sort(
    (a, b) =>
      b.alert - a.alert ||
      b.warning - a.warning ||
      b.total - a.total ||
      a.name.localeCompare(b.name),
  )
})

const totals = computed(() =>
  summaries.value.reduce(
    (acc, s) => ({
      devices: acc.devices + s.total,
      ok: acc.ok + s.ok,
      warning: acc.warning + s.warning,
      alert: acc.alert + s.alert,
    }),
    { devices: 0, ok: 0, warning: 0, alert: 0 },
  ),
)

async function load() {
  // Guard against overlapping polls / manual refreshes on slow networks.
  if (loadPending) return
  loadPending = true
  error.value = null
  try {
    devices.value = await apiFetch<Device[]>('/api/devices/devices')
    // Datacenter names are global-admin only; scoped callers fall back
    // to `#id` labels via dcName().
    if (auth.isGlobalAdmin.value) {
      datacenters.value = await apiFetch<Datacenter[]>(
        '/api/devices/datacenters',
      )
    }
    // Alert history is admin-only (ADR-0005); operators skip this call.
    if (auth.isAdmin.value) {
      const open = await apiFetch<Alert[]>(
        '/api/dashboard/alerts?acknowledged=false',
      )
      openAlertCount.value = open.length
    }
  } catch (err) {
    // A failed background refresh keeps stale data but surfaces the error.
    error.value = errorDetail(err)
  } finally {
    loadPending = false
  }
}

onMounted(async () => {
  await load()
  loading.value = false
  pollTimer = setInterval(load, POLL_MS)
})

// NOTE: registered at setup top level — lifecycle hooks called after an
// `await` lose the component instance and silently never register.
onUnmounted(() => {
  if (pollTimer !== undefined) clearInterval(pollTimer)
})

async function refresh() {
  refreshing.value = true
  try {
    await load()
  } finally {
    refreshing.value = false
  }
}
</script>

<template>
  <div>
    <AppHeader />
    <main class="p-4 space-y-4">
      <div class="flex items-center justify-between">
        <h1 class="text-xl font-semibold">Overview</h1>
        <UButton
          icon="i-heroicons-arrow-path"
          color="gray"
          :loading="refreshing"
          @click="refresh"
        >
          Refresh
        </UButton>
      </div>

      <UAlert v-if="error" color="red" variant="subtle" :title="error" />

      <div v-if="loading" class="text-sm text-gray-500">Loading…</div>

      <template v-else>
        <UAlert
          v-if="!error && devices.length === 0"
          color="blue"
          variant="subtle"
          title="No devices yet"
          description="Devices reported by operators will show up here."
        >
          <template v-if="auth.isAdmin.value" #actions>
            <UButton to="/devices" size="xs">Manage devices</UButton>
          </template>
        </UAlert>

        <template v-else>
          <UCard>
            <div class="flex flex-wrap items-center gap-x-6 gap-y-2">
              <span class="text-sm text-gray-500">
                {{ totals.devices }} devices
              </span>
              <span class="flex items-center gap-1 text-sm">
                <StateBadge state="ok" /> {{ totals.ok }}
              </span>
              <span class="flex items-center gap-1 text-sm">
                <StateBadge state="warning" /> {{ totals.warning }}
              </span>
              <span class="flex items-center gap-1 text-sm">
                <StateBadge state="alert" /> {{ totals.alert }}
              </span>
            </div>
          </UCard>

          <UAlert
            v-if="openAlertCount != null && openAlertCount > 0"
            color="amber"
            variant="subtle"
            :title="`${openAlertCount} unacknowledged alert${openAlertCount === 1 ? '' : 's'}`"
          >
            <template #actions>
              <UButton to="/alerts" size="xs">Review alerts</UButton>
            </template>
          </UAlert>

          <div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            <UCard v-for="summary in summaries" :key="summary.id">
              <template #header>
                <h2 class="font-semibold">{{ summary.name }}</h2>
              </template>
              <div class="flex items-center gap-4">
                <StateDonut
                  :ok="summary.ok"
                  :warning="summary.warning"
                  :alert="summary.alert"
                />
                <dl class="space-y-1 text-sm">
                  <div class="flex items-center gap-2">
                    <dt><StateBadge state="ok" /></dt>
                    <dd>{{ summary.ok }}</dd>
                  </div>
                  <div class="flex items-center gap-2">
                    <dt><StateBadge state="warning" /></dt>
                    <dd>{{ summary.warning }}</dd>
                  </div>
                  <div class="flex items-center gap-2">
                    <dt><StateBadge state="alert" /></dt>
                    <dd>{{ summary.alert }}</dd>
                  </div>
                </dl>
              </div>
            </UCard>
          </div>
        </template>
      </template>
    </main>
  </div>
</template>
