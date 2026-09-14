<script setup lang="ts">
import type {
  AcknowledgeResponse,
  Alert,
  Datacenter,
  StreamEvent,
} from '~/types/api'

const auth = useAuth()
const { apiFetch } = useApi()
const toast = useToast()

// Admin-only (dashboard service 403s operators; ADR-0005).
if (!auth.isAdmin.value) {
  await navigateTo('/')
}

const alerts = ref<Alert[]>([])
const datacenters = ref<Datacenter[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

const filters = reactive({
  acknowledged: 'unacknowledged' as 'all' | 'unacknowledged' | 'acknowledged',
  datacenter_id: undefined as number | undefined,
})

async function load() {
  loading.value = true
  error.value = null
  try {
    const params = new URLSearchParams()
    if (filters.acknowledged === 'acknowledged') params.set('acknowledged', 'true')
    if (filters.acknowledged === 'unacknowledged') params.set('acknowledged', 'false')
    if (filters.datacenter_id != null) {
      params.set('datacenter_id', String(filters.datacenter_id))
    }
    const qs = params.toString()
    alerts.value = await apiFetch<Alert[]>(
      `/api/dashboard/alerts${qs ? `?${qs}` : ''}`,
    )
  } catch (err) {
    error.value = errorDetail(err)
  } finally {
    loading.value = false
  }
}

watch(filters, load)

onMounted(async () => {
  if (auth.isGlobalAdmin.value) {
    try {
      datacenters.value = await apiFetch<Datacenter[]>('/api/devices/datacenters')
    } catch {
      // Non-fatal: the datacenter filter just stays empty.
    }
  }
  await load()
})

const columns = [
  { key: 'occurred_at', label: 'When' },
  { key: 'device_id', label: 'Device' },
  { key: 'datacenter_id', label: 'Datacenter' },
  { key: 'transition', label: 'Transition' },
  { key: 'reporter', label: 'Reporter' },
  { key: 'status', label: 'Status' },
  { key: 'actions', label: '' },
]

async function acknowledge(alert: Alert) {
  try {
    const res = await apiFetch<AcknowledgeResponse>(
      `/api/dashboard/alerts/${alert.id}/acknowledge`,
      { method: 'POST' },
    )
    Object.assign(alert, res)
    if (!res.device_reset_ok) {
      // ADR-0005: ack succeeded but the device could not be reset to ok.
      toast.add({
        title: 'Acknowledged, but the device could not be reset to ok',
        color: 'amber',
      })
    }
  } catch (err) {
    toast.add({ title: errorDetail(err), color: 'red' })
  }
}

// --- live stream (SSE) ---
// NOTE: EventSource cannot send an Authorization header, but GET /stream
// requires a Bearer token (HTTPBearer). So we consume the stream with fetch
// + a manual SSE frame parser, attaching the in-memory access token.
onMounted(() => {
  let stopped = false
  let abort: AbortController | null = null

  const handlePayload = (raw: string) => {
    let event: StreamEvent
    try {
      event = JSON.parse(raw)
    } catch {
      return
    }
    if (event.type === 'device_status_changed') {
      if (event.new_state === 'ok') {
        // Recoveries stream but have no alert row (ADR-0005).
        toast.add({
          title: `Device #${event.device_id} recovered to ok`,
          color: 'green',
        })
      } else {
        toast.add({
          title: `Device #${event.device_id}: ${event.old_state} → ${event.new_state}`,
          color: event.new_state === 'alert' ? 'red' : 'amber',
        })
        // Refresh the list: the event itself carries no alert id.
        load()
      }
    } else if (event.type === 'alert_acknowledged_and_resolved') {
      load()
    }
  }

  const connect = async () => {
    while (!stopped) {
      abort = new AbortController()
      try {
        let token = auth.accessToken.value
        if (!token) {
          if (!(await auth.refresh())) return
          token = auth.accessToken.value
        }
        const res = await fetch('/api/dashboard/stream', {
          headers: {
            Authorization: `Bearer ${token}`,
            Accept: 'text/event-stream',
          },
          signal: abort.signal,
        })
        if (res.status === 401) {
          // Token expired between calls: rotate once and reconnect.
          if (await auth.refresh()) continue
          return
        }
        if (!res.ok || !res.body) {
          await new Promise((r) => setTimeout(r, 3000))
          continue
        }
        const reader = res.body.getReader()
        const decoder = new TextDecoder()
        let buf = ''
        for (;;) {
          const { done, value } = await reader.read()
          if (done) break
          buf += decoder.decode(value, { stream: true })
          let idx: number
          while ((idx = buf.indexOf('\n\n')) >= 0) {
            const frame = buf.slice(0, idx)
            buf = buf.slice(idx + 2)
            for (const line of frame.split('\n')) {
              if (line.startsWith('data:')) {
                handlePayload(line.slice(5).trim())
              }
            }
          }
        }
      } catch {
        // Aborted on unmount or transient network failure.
      }
      if (!stopped) {
        await new Promise((r) => setTimeout(r, 3000))
      }
    }
  }

  connect()

  onUnmounted(() => {
    stopped = true
    abort?.abort()
  })
})
</script>

<template>
  <div>
    <AppHeader />
    <main class="p-4 space-y-4">
      <h1 class="text-xl font-semibold">Alerts</h1>

      <div class="flex gap-4">
        <UFormGroup label="Status">
          <USelect
            v-model="filters.acknowledged"
            :options="[
              { label: 'Unacknowledged', value: 'unacknowledged' },
              { label: 'Acknowledged', value: 'acknowledged' },
              { label: 'All', value: 'all' },
            ]"
          />
        </UFormGroup>
        <UFormGroup v-if="auth.isGlobalAdmin.value" label="Datacenter">
          <USelect
            v-model="filters.datacenter_id"
            :options="[
              { label: 'All', value: undefined },
              ...datacenters.map((d) => ({ label: d.name, value: d.id })),
            ]"
          />
        </UFormGroup>
      </div>

      <UAlert v-if="error" color="red" variant="subtle" :title="error" />
      <UTable :rows="alerts" :columns="columns" :loading="loading">
        <template #occurred_at-data="{ row }">
          {{ new Date(row.occurred_at).toLocaleString() }}
        </template>
        <template #device_id-data="{ row }">#{{ row.device_id }}</template>
        <template #datacenter_id-data="{ row }">
          {{ datacenters.find((d) => d.id === row.datacenter_id)?.name ?? `#${row.datacenter_id}` }}
        </template>
        <template #transition-data="{ row }">
          <div class="flex items-center gap-1">
            <StateBadge :state="row.old_state" />
            <span>→</span>
            <StateBadge :state="row.new_state" />
          </div>
        </template>
        <template #status-data="{ row }">
          <UBadge v-if="row.acknowledged_at" color="green" variant="subtle">
            Acked by {{ row.acknowledged_by }}
          </UBadge>
          <UBadge v-else color="amber" variant="subtle">Open</UBadge>
        </template>
        <template #actions-data="{ row }">
          <UButton
            v-if="!row.acknowledged_at"
            size="xs"
            @click="acknowledge(row)"
          >
            Acknowledge
          </UButton>
        </template>
      </UTable>
    </main>
  </div>
</template>
