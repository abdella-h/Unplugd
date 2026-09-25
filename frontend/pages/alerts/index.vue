<script setup lang="ts">
import type { AcknowledgeResponse, Alert } from '~/types/api'

definePageMeta({ title: 'Alerts' })

type AlertTab = 'open' | 'acknowledged'
type DatacenterFilter = 'all' | number
type AcknowledgmentIntent = 'acknowledge' | 'retry'

const auth = useAuth()
const route = useRoute()
const workspace = useWorkspace()
const realtime = useRealtime()
const { apiFetch } = useApi()

const activeTab = ref<AlertTab>(route.query.tab === 'acknowledged' ? 'acknowledged' : 'open')
const datacenterFilter = ref<DatacenterFilter>('all')
const mobileFilterDraft = ref<DatacenterFilter>('all')
const mobileFilterOpen = ref(false)
const alerts = ref<Alert[]>([])
const isInitialLoading = ref(true)
const isRefreshing = ref(false)
const resetFailureRows = ref<Record<number, Alert>>({})
const lastFocusedAlertId = ref<number | null>(null)
const loadError = ref<string | null>(null)
const hasLoadedAlerts = ref(false)
const lastAlertsLoadedAt = ref<number | null>(null)
const isDatacentersLoading = ref(false)
const datacenterLoadError = ref<string | null>(null)
const acknowledgeDialogOpen = ref(false)
const acknowledgeIntent = ref<AcknowledgmentIntent>('acknowledge')
const acknowledgeTarget = ref<Alert | null>(null)
const pendingActions = reactive<Record<number, boolean>>({})
const actionErrors = reactive<Record<number, string>>({})
const sessionResetFailures = useState<Record<number, boolean>>(
  'alerts:session-reset-failures',
  () => ({}),
)
const sessionIdentity = useState<string | null>('alerts:session-identity', () => null)
const currentIdentity = auth.user.value
  ? `${auth.user.value.username}|${auth.user.value.role}|${auth.user.value.dcId ?? ''}`
  : null
if (sessionIdentity.value !== currentIdentity) {
  sessionIdentity.value = currentIdentity
  sessionResetFailures.value = {}
  resetFailureRows.value = {}
}

const resetFailureMessage = 'Alert acknowledged; device reset failed'
const resetFailureItems = computed(() => Object.values(resetFailureRows.value))
let alertLoadSequence = 0

if (!auth.isAdmin.value) {
  void navigateTo('/')
}

const datacenterOptions = computed<{ label: string; value: DatacenterFilter }[]>(() => [
  { label: 'All datacenters', value: 'all' },
  ...workspace.datacenters.value
    .map((datacenter) => ({
      label: datacenter.name,
      value: datacenter.id as DatacenterFilter,
    }))
    .sort((left, right) => left.label.localeCompare(right.label)),
])

const deviceFilter = computed<number | null>(() => {
  const rawValue = Array.isArray(route.query.device_id) ? route.query.device_id[0] : route.query.device_id
  const parsed = Number(rawValue)
  return rawValue != null && Number.isInteger(parsed) && parsed > 0 ? parsed : null
})

const alertFocusId = computed<number | null>(() => {
  const rawValue = Array.isArray(route.query.alert_id) ? route.query.alert_id[0] : route.query.alert_id
  const parsed = Number(rawValue)
  return rawValue != null && Number.isInteger(parsed) && parsed > 0 ? parsed : null
})

function isFocusedAlert(alertId: number): boolean {
  return alertFocusId.value === alertId
}

async function focusAlert() {
  if (!alertFocusId.value || !import.meta.client || lastFocusedAlertId.value === alertFocusId.value) return
  await nextTick()
  const attribute = window.matchMedia('(min-width: 1024px)').matches ? 'data-alert-id' : 'data-alert-id-mobile'
  const target = document.querySelector<HTMLElement>(`[${attribute}="${alertFocusId.value}"]`)
  if (!target) return
  lastFocusedAlertId.value = alertFocusId.value
  target.scrollIntoView({ block: 'center' })
  target.focus()
}

const deviceFilterLabel = computed(() =>
  deviceFilter.value ? `Device #${deviceFilter.value}` : null,
)

const selectedDatacenterName = computed(() => {
  if (datacenterFilter.value === 'all') return null
  return workspace.datacenterName(datacenterFilter.value)
})

const resultLabel = computed(() => {
  const count = alerts.value.length
  const label = activeTab.value === 'open' ? 'Open Alert' : 'Acknowledged Alert'
  const suffix = deviceFilterLabel.value ? ` for ${deviceFilterLabel.value}` : ''
  return `${count} ${label}${count === 1 ? '' : 's'}${suffix}`
})

const emptyTitle = computed(() => {
  const label = activeTab.value === 'open' ? 'Open Alerts' : 'Acknowledged Alerts'
  if (deviceFilterLabel.value) return `No ${label} for ${deviceFilterLabel.value}`
  return selectedDatacenterName.value
    ? `No ${label} in ${selectedDatacenterName.value}`
    : `No ${label}`
})

const emptyDescription = computed(() => {
  if (deviceFilterLabel.value) {
    return 'Clear the Device focus to view Alerts across the current scope.'
  }
  if (selectedDatacenterName.value) {
    return 'Clear the Datacenter filter to view results across the current scope.'
  }
  return activeTab.value === 'open'
    ? 'New Alerts appear when a Device reports a warning or alert State.'
    : 'Alerts appear here after they have been acknowledged.'
})

const acknowledgeTitle = computed(() =>
  acknowledgeIntent.value === 'retry'
    ? 'Retry device reset?'
    : 'Acknowledge this Open Alert?',
)

const acknowledgeDescription = computed(() =>
  acknowledgeIntent.value === 'retry'
    ? 'Repeat the Alert acknowledgment request and try resetting the Device to the reported ok State again. The original Acknowledgment will remain unchanged.'
    : 'Acknowledge this Open Alert and request a reset of the Device to the reported ok State. The Acknowledgment can succeed even when the reset does not.',
)

const acknowledgeLabel = computed(() =>
  acknowledgeIntent.value === 'retry' ? 'Retry Reset' : 'Acknowledge',
)

const acknowledgeLoading = computed(
  () => acknowledgeTarget.value?.id != null && isActionPending(acknowledgeTarget.value.id),
)

const fetchedTimeLabel = computed(() => {
  if (lastAlertsLoadedAt.value == null) return ''
  return new Date(lastAlertsLoadedAt.value).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
  })
})

function formatTimestamp(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString([], {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

function formatFetchedTime(value: number) {
  return new Date(value).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

function stateLabel(state: Alert['old_state']) {
  return state === 'ok' ? 'OK' : `${state[0]?.toUpperCase() ?? ''}${state.slice(1)}`
}

function isActionPending(alertId: number) {
  return pendingActions[alertId] === true
}

function hasResetFailure(alertId: number) {
  return sessionResetFailures.value[alertId] === true
}

function setResetFailure(alert: Alert) {
  sessionResetFailures.value = {
    ...sessionResetFailures.value,
    [alert.id]: true,
  }
  resetFailureRows.value = {
    ...resetFailureRows.value,
    [alert.id]: alert,
  }
}

function clearResetFailure(alertId: number) {
  if (alertId in sessionResetFailures.value) {
    const next = { ...sessionResetFailures.value }
    delete next[alertId]
    sessionResetFailures.value = next
  }
  if (alertId in resetFailureRows.value) {
    const nextRows = { ...resetFailureRows.value }
    delete nextRows[alertId]
    resetFailureRows.value = nextRows
  }
}

function clearDatacenterFilter() {
  datacenterFilter.value = 'all'
}

function clearDeviceFilter() {
  void navigateTo('/alerts')
}

function openMobileFilters() {
  mobileFilterDraft.value = datacenterFilter.value
  mobileFilterOpen.value = true
}

function applyMobileFilters() {
  datacenterFilter.value = mobileFilterDraft.value
  mobileFilterOpen.value = false
}

function cancelMobileFilters() {
  mobileFilterOpen.value = false
}

async function loadDatacenters() {
  if (!auth.isGlobalAdmin.value) return
  if (workspace.datacenters.value.length > 0) {
    datacenterLoadError.value = null
    return
  }

  isDatacentersLoading.value = true
  datacenterLoadError.value = null
  try {
    const metadataLoaded = await workspace.loadDatacenters()
    if (!metadataLoaded) throw new Error('Datacenter filter options could not be loaded.')
  } catch (err) {
    datacenterLoadError.value = errorDetail(
      err,
      'Datacenter filter options could not be loaded.',
    )
  } finally {
    isDatacentersLoading.value = false
  }
}

async function loadAlerts(background = false) {
  const preserveData = background && hasLoadedAlerts.value
  const requestId = ++alertLoadSequence

  isRefreshing.value = preserveData
  isInitialLoading.value = !preserveData
  loadError.value = null

  if (!preserveData) {
    alerts.value = []
    hasLoadedAlerts.value = false
    lastAlertsLoadedAt.value = null
  }

  const acknowledged = activeTab.value === 'open' ? 'false' : 'true'
  const params = new URLSearchParams({ acknowledged })
  if (datacenterFilter.value !== 'all') {
    params.set('datacenter_id', String(datacenterFilter.value))
  }

  try {
    const result = await apiFetch<Alert[]>(
      `/api/dashboard/alerts?${params.toString()}`,
    )
    if (requestId !== alertLoadSequence) return

    alerts.value = deviceFilter.value
      ? result.filter((alert) => alert.device_id === deviceFilter.value)
      : result
    hasLoadedAlerts.value = true
    lastAlertsLoadedAt.value = Date.now()
    void focusAlert()
    workspace.markFresh()
  } catch (err) {
    if (requestId !== alertLoadSequence) return
    loadError.value = errorDetail(err, 'The Alert list could not be fetched.')
    workspace.markStale()
  } finally {
    if (requestId === alertLoadSequence) {
      isInitialLoading.value = false
      isRefreshing.value = false
    }
  }
}

function refreshAlerts() {
  void loadAlerts(hasLoadedAlerts.value)
}

function openAcknowledgment(alert: Alert, intent: AcknowledgmentIntent) {
  if (isActionPending(alert.id)) return
  if (intent === 'acknowledge' && alert.acknowledged_at) return
  if (intent === 'retry' && !hasResetFailure(alert.id)) return

  acknowledgeTarget.value = alert
  acknowledgeIntent.value = intent
  acknowledgeDialogOpen.value = true
}

async function submitAcknowledgment() {
  const target = acknowledgeTarget.value
  if (!target || isActionPending(target.id)) return

  const intent = acknowledgeIntent.value
  const requestGeneration = workspace.generation.value
  alertLoadSequence += 1
  isRefreshing.value = false
  pendingActions[target.id] = true
  delete actionErrors[target.id]

  try {
    const response = await apiFetch<AcknowledgeResponse>(
      `/api/dashboard/alerts/${target.id}/acknowledge`,
      { method: 'POST' },
    )
    if (workspace.generation.value !== requestGeneration) return

    const index = alerts.value.findIndex((alert) => alert.id === response.id)
    if (index !== -1) alerts.value[index] = response

    if (response.device_reset_ok) {
      clearResetFailure(target.id)
    } else {
      setResetFailure(response)
    }

    if (intent === 'acknowledge' && activeTab.value === 'open') {
      if (!response.device_reset_ok) {
        alerts.value = alerts.value.filter((alert) => alert.id !== target.id)
        activeTab.value = 'acknowledged'
      } else {
        alerts.value = alerts.value.filter((alert) => alert.id !== target.id)
      }
    }

    void workspace.refreshAlertCount()
  } catch (err) {
    if (workspace.generation.value !== requestGeneration) return
    actionErrors[target.id] = errorDetail(
      err,
      intent === 'retry'
        ? 'Retry Reset failed. The Alert remains acknowledged.'
        : 'The Alert could not be acknowledged.',
    )
  } finally {
    if (workspace.generation.value === requestGeneration) {
      delete pendingActions[target.id]
      acknowledgeDialogOpen.value = false
      acknowledgeTarget.value = null
    }
  }
}

async function handleTabKeydown(event: KeyboardEvent, currentTab: AlertTab) {
  let nextTab: AlertTab | null = null
  if (event.key === 'ArrowRight' || event.key === 'ArrowDown') {
    nextTab = currentTab === 'open' ? 'acknowledged' : 'open'
  } else if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') {
    nextTab = currentTab === 'acknowledged' ? 'open' : 'acknowledged'
  } else if (event.key === 'Home') {
    nextTab = 'open'
  } else if (event.key === 'End') {
    nextTab = 'acknowledged'
  }

  if (!nextTab) return
  event.preventDefault()
  activeTab.value = nextTab
  await nextTick()
  document.getElementById(`alerts-tab-${nextTab}`)?.focus()
}

watch(
  () => [route.query.tab, route.query.device_id, route.query.alert_id],
  ([tab]) => {
    lastFocusedAlertId.value = null
    const nextTab: AlertTab = tab === 'acknowledged' ? 'acknowledged' : 'open'
    if (activeTab.value !== nextTab) activeTab.value = nextTab
  },
)

watch([activeTab, datacenterFilter, deviceFilter, alertFocusId], () => {
  if (auth.isAdmin.value) void loadAlerts()
})

watch(workspace.generation, () => {
  alertLoadSequence += 1
  alerts.value = []
  hasLoadedAlerts.value = false
  isInitialLoading.value = Boolean(auth.isAdmin.value)
  isRefreshing.value = false
  loadError.value = null
  for (const alertId of Object.keys(pendingActions)) delete pendingActions[Number(alertId)]
  for (const alertId of Object.keys(actionErrors)) delete actionErrors[Number(alertId)]
  acknowledgeDialogOpen.value = false
  acknowledgeTarget.value = null
  resetFailureRows.value = {}
  datacenterFilter.value = 'all'
  activeTab.value = 'open'
  if (auth.isAdmin.value) {
    void Promise.all([loadDatacenters(), loadAlerts()])
  }
})

watch(realtime.lastEvent, (event) => {
  if (!event || !auth.isAdmin.value) return
  const affectsAlerts =
    event.type === 'alert_acknowledged_and_resolved' ||
    (event.type === 'device_status_changed' && event.new_state !== 'ok')
  if (affectsAlerts) void loadAlerts(true)
})

watch(
  () => {
    const user = auth.user.value
    return user ? `${user.username}|${user.role}|${user.dcId ?? ''}` : ''
  },
  (identity, previousIdentity) => {
    if (!identity || (previousIdentity && identity !== previousIdentity)) {
      sessionResetFailures.value = {}
      resetFailureRows.value = {}
      sessionIdentity.value = identity || null
    }
  },
)

onMounted(() => {
  if (!auth.isAdmin.value) return
  void Promise.all([loadDatacenters(), loadAlerts()])
})
</script>

<template>
  <div class="space-y-5">
    <AppPageHeader
      title="Alerts"
      description="Review reported State transitions, acknowledge operational Alerts, and keep Device reset outcomes separate."
    >
      <template #actions>
        <div class="flex items-center gap-3">
          <span
            v-if="isRefreshing"
            class="flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400"
            role="status"
          >
            <UIcon name="i-heroicons-arrow-path" class="h-3.5 w-3.5 animate-spin" />
            Refreshing Alerts
          </span>
          <UButton
            icon="i-heroicons-arrow-path"
            color="gray"
            variant="outline"
            :loading="isRefreshing"
            :disabled="isInitialLoading"
            @click="refreshAlerts"
          >
            Refresh
          </UButton>
        </div>
      </template>
    </AppPageHeader>

    <section class="monitor-panel p-4" aria-labelledby="alerts-workflow-label">
      <div class="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p
            id="alerts-workflow-label"
            class="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500 dark:text-slate-400"
          >
            Alert workflow
          </p>
          <div
            class="mt-2 inline-grid w-full grid-cols-2 rounded-lg border border-[var(--monitor-border)] bg-[var(--monitor-raised)] p-1 sm:w-auto"
            role="tablist"
            aria-label="Alert workflow"
          >
            <button
              id="alerts-tab-open"
              type="button"
              role="tab"
              aria-controls="alerts-panel"
              :aria-selected="activeTab === 'open'"
              :tabindex="activeTab === 'open' ? 0 : -1"
              class="min-h-10 rounded-md border px-3 text-sm font-semibold focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-500"
              :class="activeTab === 'open'
                ? 'border-[var(--monitor-border)] bg-[var(--monitor-surface)] text-cyan-700 shadow-sm dark:text-cyan-200'
                : 'border-transparent text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white'"
              @click="activeTab = 'open'"
              @keydown="handleTabKeydown($event, 'open')"
            >
              Open Alerts
            </button>
            <button
              id="alerts-tab-acknowledged"
              type="button"
              role="tab"
              aria-controls="alerts-panel"
              :aria-selected="activeTab === 'acknowledged'"
              :tabindex="activeTab === 'acknowledged' ? 0 : -1"
              class="min-h-10 rounded-md border px-3 text-sm font-semibold focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-500"
              :class="activeTab === 'acknowledged'
                ? 'border-[var(--monitor-border)] bg-[var(--monitor-surface)] text-cyan-700 shadow-sm dark:text-cyan-200'
                : 'border-transparent text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white'"
              @click="activeTab = 'acknowledged'"
              @keydown="handleTabKeydown($event, 'acknowledged')"
            >
              Acknowledged
            </button>
          </div>
        </div>

        <UButton
          v-if="auth.isGlobalAdmin.value"
          class="w-full lg:hidden"
          icon="i-heroicons-funnel"
          color="gray"
          variant="outline"
          @click="openMobileFilters"
        >
          Filter by Datacenter
        </UButton>
        <div v-if="auth.isGlobalAdmin.value" class="hidden w-full lg:block lg:max-w-xs">
          <div class="mb-1.5 flex items-center justify-between gap-3">
            <label
              for="alerts-datacenter-filter"
              class="text-xs font-semibold uppercase tracking-[0.1em] text-slate-500 dark:text-slate-400"
            >
              Datacenter
            </label>
            <span
              v-if="isDatacentersLoading"
              class="flex items-center gap-1 text-xs text-slate-500 dark:text-slate-400"
              role="status"
            >
              <UIcon name="i-heroicons-arrow-path" class="h-3 w-3 animate-spin" />
              Loading
            </span>
          </div>
          <USelect
            id="alerts-datacenter-filter"
            v-model="datacenterFilter"
            :options="datacenterOptions"
            :disabled="isDatacentersLoading"
            class="w-full"
          />
          <div
            v-if="datacenterLoadError"
            class="mt-2 flex items-start justify-between gap-2 text-xs text-red-600 dark:text-red-300"
            role="alert"
          >
            <span>{{ datacenterLoadError }}</span>
            <UButton
              type="button"
              color="red"
              variant="link"
              size="xs"
              class="shrink-0"
              @click="loadDatacenters"
            >
              Retry
            </UButton>
          </div>
        </div>
        <div v-if="deviceFilterLabel" class="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
          <span>Focused on {{ deviceFilterLabel }}</span>
          <UButton color="gray" variant="link" size="xs" @click="clearDeviceFilter">Clear</UButton>
        </div>
      </div>
    </section>

    <UAlert
      v-if="resetFailureItems.length"
      color="amber"
      variant="subtle"
      :title="resetFailureMessage"
      description="The Alert is acknowledged, but its Device is not confirmed reset to ok."
      role="alert"
    >
      <template #actions>
        <UButton
          v-for="alert in resetFailureItems"
          :key="alert.id"
          color="amber"
          variant="soft"
          size="xs"
          :loading="isActionPending(alert.id)"
          :disabled="isActionPending(alert.id)"
          @click="openAcknowledgment(alert, 'retry')"
        >
          Retry reset for Alert #{{ alert.id }}
        </UButton>
      </template>
    </UAlert>

    <div
      v-if="hasLoadedAlerts"
      class="flex flex-wrap items-center justify-between gap-2 px-1 text-xs"
    >
      <p class="font-medium text-slate-600 dark:text-slate-300" aria-live="polite">
        {{ resultLabel }}
      </p>
      <p
        v-if="loadError"
        class="flex items-center gap-1.5 font-medium text-amber-700 dark:text-amber-300"
      >
        <UIcon name="i-heroicons-exclamation-triangle" class="h-3.5 w-3.5" />
        Stale data · fetched {{ formatFetchedTime(lastAlertsLoadedAt ?? 0) }}
      </p>
      <p v-else-if="lastAlertsLoadedAt" class="text-slate-500 dark:text-slate-400">
        Fetched {{ fetchedTimeLabel }}
      </p>
    </div>

    <div
      id="alerts-panel"
      role="tabpanel"
      :aria-labelledby="`alerts-tab-${activeTab}`"
      :aria-busy="isInitialLoading || isRefreshing"
    >
      <div v-if="isInitialLoading" class="monitor-panel p-4" role="status" aria-busy="true">
        <span class="sr-only">
          Loading {{ activeTab === 'open' ? 'Open Alerts' : 'Acknowledged Alerts' }}
        </span>
        <div class="space-y-3" aria-hidden="true">
          <div
            v-for="row in 5"
            :key="row"
            class="flex items-center gap-4 rounded-md border border-[var(--monitor-border)] p-4"
          >
            <div class="monitor-skeleton h-6 w-20 rounded-md" />
            <div class="min-w-0 flex-1">
              <div class="monitor-skeleton h-4 w-36 rounded" />
              <div class="monitor-skeleton mt-2 h-3 w-52 max-w-full rounded" />
            </div>
            <div class="monitor-skeleton hidden h-4 w-28 rounded sm:block" />
            <div class="monitor-skeleton h-8 w-24 rounded-md" />
          </div>
        </div>
      </div>

      <template v-else>
        <UAlert
          v-if="loadError"
          class="mb-4"
          :color="hasLoadedAlerts ? 'amber' : 'red'"
          variant="subtle"
          :title="hasLoadedAlerts ? 'Alert data is stale' : 'Alerts could not be loaded'"
          :description="loadError"
        >
          <template #actions>
            <UButton
              type="button"
              color="gray"
              variant="outline"
              size="xs"
              :loading="isRefreshing"
              @click="refreshAlerts"
            >
              Retry
            </UButton>
          </template>
        </UAlert>

        <div v-if="loadError && !hasLoadedAlerts" class="monitor-panel">
          <AppEmptyState
            icon="i-heroicons-exclamation-triangle"
            title="Alert list unavailable"
            description="The current Open or Acknowledged Alerts could not be fetched. Retry when the service is available."
          >
            <template #actions>
              <UButton type="button" color="primary" @click="refreshAlerts">Retry</UButton>
            </template>
          </AppEmptyState>
        </div>

        <div v-else-if="alerts.length" class="monitor-table" :aria-busy="isRefreshing">
          <div class="hidden lg:block">
            <table class="w-full table-fixed text-left text-xs">
              <caption class="sr-only">
                {{ activeTab === 'open' ? 'Open Alerts' : 'Acknowledged Alerts' }}
              </caption>
              <thead class="border-b border-[var(--monitor-border)] bg-[var(--monitor-raised)] text-[11px] font-semibold uppercase tracking-[0.08em] text-slate-500 dark:text-slate-400">
                <tr>
                  <th scope="col" class="w-[112px] px-3 py-2.5">Alert</th>
                  <th scope="col" class="w-[104px] px-3 py-2.5">Device</th>
                  <th scope="col" class="hidden w-[136px] px-3 py-2.5 xl:table-cell">Datacenter</th>
                  <th scope="col" class="w-[138px] px-3 py-2.5">Transition</th>
                  <th scope="col" class="hidden w-[154px] px-3 py-2.5 2xl:table-cell">Occurred</th>
                  <th scope="col" class="hidden w-[104px] px-3 py-2.5 xl:table-cell">Reported by</th>
                  <th scope="col" class="hidden w-[150px] px-3 py-2.5 xl:table-cell">Acknowledgment</th>
                  <th scope="col" class="w-[228px] px-3 py-2.5 text-right">Action</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-[var(--monitor-border)]">
                <tr
                  v-for="alert in alerts"
                  :key="alert.id"
                  :data-alert-id="alert.id"
                  tabindex="-1"
                  class="align-top transition-colors hover:bg-[var(--monitor-raised)]"
                  :class="isFocusedAlert(alert.id) ? 'bg-cyan-50/70 ring-2 ring-inset ring-primary-700 dark:ring-primary-300 dark:bg-cyan-950/30' : ''"
                  :aria-current="isFocusedAlert(alert.id) ? 'true' : undefined"
                >
                  <td class="px-3 py-3">
                    <div class="flex flex-col items-start gap-1.5">
                      <StateBadge :state="alert.new_state" />
                      <span class="text-slate-500 dark:text-slate-400">Alert #{{ alert.id }}</span>
                    </div>
                  </td>
                  <td class="px-3 py-3">
                    <NuxtLink
                      :to="`/devices/${alert.device_id}`"
                      class="font-medium text-cyan-700 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-500 dark:text-cyan-300"
                    >
                      Device #{{ alert.device_id }}
                    </NuxtLink>
                  </td>
                  <td class="hidden px-3 py-3 font-medium xl:table-cell">
                    {{ workspace.datacenterName(alert.datacenter_id) }}
                  </td>
                  <td class="px-3 py-3">
                    <div class="flex items-center gap-1.5 whitespace-nowrap">
                      <span class="text-slate-500 dark:text-slate-400">{{ stateLabel(alert.old_state) }}</span>
                      <UIcon name="i-heroicons-arrow-right" class="h-3 w-3 text-slate-400" />
                      <span class="font-semibold">{{ stateLabel(alert.new_state) }}</span>
                    </div>
                  </td>
                  <td class="hidden whitespace-nowrap px-3 py-3 text-slate-600 dark:text-slate-300 2xl:table-cell">
                    <time :datetime="alert.occurred_at">{{ formatTimestamp(alert.occurred_at) }}</time>
                  </td>
                  <td class="hidden px-3 py-3 xl:table-cell">
                    <span class="text-slate-500 dark:text-slate-400">Reported by</span>
                    <span class="ml-1 font-medium">{{ alert.reporter }}</span>
                  </td>
                  <td class="hidden px-3 py-3 xl:table-cell">
                    <template v-if="alert.acknowledged_at">
                      <UBadge color="green" variant="subtle" icon="i-heroicons-check-circle">
                        Acknowledged
                      </UBadge>
                      <div class="mt-1 leading-4 text-slate-500 dark:text-slate-400">
                        by {{ alert.acknowledged_by }}
                      </div>
                      <time
                        :datetime="alert.acknowledged_at"
                        class="block text-[11px] text-slate-500 dark:text-slate-400"
                      >
                        {{ formatTimestamp(alert.acknowledged_at) }}
                      </time>
                    </template>
                    <UBadge v-else color="amber" variant="subtle" icon="i-heroicons-bell-alert">
                      Open Alert
                    </UBadge>
                  </td>
                  <td class="px-3 py-3 text-right">
                    <div class="flex flex-col items-end gap-1.5">
                      <UButton
                        v-if="!alert.acknowledged_at"
                        type="button"
                        size="xs"
                        :loading="isActionPending(alert.id)"
                        :disabled="isActionPending(alert.id)"
                        @click="openAcknowledgment(alert, 'acknowledge')"
                      >
                        {{ isActionPending(alert.id) ? 'Acknowledging…' : 'Acknowledge' }}
                      </UButton>
                      <template v-else-if="hasResetFailure(alert.id)">
                        <p class="max-w-[220px] rounded-md border border-amber-300 bg-amber-50 p-2 text-left text-[11px] font-medium leading-4 text-amber-900 dark:border-amber-700/70 dark:bg-amber-950/40 dark:text-amber-200">
                          {{ resetFailureMessage }}
                        </p>
                        <UButton
                          type="button"
                          color="amber"
                          variant="soft"
                          size="xs"
                          icon="i-heroicons-arrow-path"
                          :loading="isActionPending(alert.id)"
                          :disabled="isActionPending(alert.id)"
                          @click="openAcknowledgment(alert, 'retry')"
                        >
                          {{ isActionPending(alert.id) ? 'Retrying reset…' : 'Retry Reset' }}
                        </UButton>
                      </template>
                      <span v-else class="text-slate-400 dark:text-slate-600" aria-hidden="true">—</span>
                      <p
                        v-if="actionErrors[alert.id]"
                        class="max-w-[220px] text-left text-[11px] font-medium leading-4 text-red-600 dark:text-red-300"
                        role="alert"
                      >
                        {{ actionErrors[alert.id] }}
                      </p>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <ul class="divide-y divide-[var(--monitor-border)] lg:hidden">
            <li
              v-for="alert in alerts"
              :key="alert.id"
              :data-alert-id-mobile="alert.id"
              tabindex="-1"
              class="p-4"
              :class="isFocusedAlert(alert.id) ? 'bg-cyan-50/70 ring-2 ring-inset ring-primary-700 dark:ring-primary-300 dark:bg-cyan-950/30' : ''"
              :aria-current="isFocusedAlert(alert.id) ? 'true' : undefined"
            >
              <div class="flex items-start justify-between gap-3">
                <div class="min-w-0">
                  <NuxtLink
                    :to="`/devices/${alert.device_id}`"
                    class="text-base font-semibold text-cyan-700 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-500 dark:text-cyan-300"
                  >
                    Device #{{ alert.device_id }}
                  </NuxtLink>
                  <p class="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
                    Alert #{{ alert.id }} · {{ workspace.datacenterName(alert.datacenter_id) }}
                  </p>
                </div>
                <div class="flex shrink-0 flex-col items-end gap-1.5">
                  <StateBadge :state="alert.new_state" />
                  <UBadge
                    v-if="alert.acknowledged_at"
                    color="green"
                    variant="subtle"
                    icon="i-heroicons-check-circle"
                  >
                    Acknowledged
                  </UBadge>
                  <UBadge v-else color="amber" variant="subtle" icon="i-heroicons-bell-alert">
                    Open Alert
                  </UBadge>
                </div>
              </div>

              <dl class="mt-4 grid grid-cols-2 gap-x-4 gap-y-3 text-xs">
                <div>
                  <dt class="font-medium text-slate-500 dark:text-slate-400">Transition</dt>
                  <dd class="mt-1 font-semibold">
                    {{ stateLabel(alert.old_state) }} → {{ stateLabel(alert.new_state) }}
                  </dd>
                </div>
                <div>
                  <dt class="font-medium text-slate-500 dark:text-slate-400">Occurred</dt>
                  <dd class="mt-1">
                    <time :datetime="alert.occurred_at">{{ formatTimestamp(alert.occurred_at) }}</time>
                  </dd>
                </div>
                <div>
                  <dt class="font-medium text-slate-500 dark:text-slate-400">Reported by</dt>
                  <dd class="mt-1 font-medium">{{ alert.reporter }}</dd>
                </div>
                <div>
                  <dt class="font-medium text-slate-500 dark:text-slate-400">Acknowledgment</dt>
                  <dd v-if="alert.acknowledged_at" class="mt-1">
                    by {{ alert.acknowledged_by }}
                    <time
                      :datetime="alert.acknowledged_at"
                      class="mt-0.5 block text-[11px] text-slate-500 dark:text-slate-400"
                    >
                      {{ formatTimestamp(alert.acknowledged_at) }}
                    </time>
                  </dd>
                  <dd v-else class="mt-1">Not acknowledged</dd>
                </div>
              </dl>

              <div class="mt-4 border-t border-[var(--monitor-border)] pt-3">
                <UButton
                  v-if="!alert.acknowledged_at"
                  type="button"
                  size="sm"
                  block
                  :loading="isActionPending(alert.id)"
                  :disabled="isActionPending(alert.id)"
                  @click="openAcknowledgment(alert, 'acknowledge')"
                >
                  {{ isActionPending(alert.id) ? 'Acknowledging…' : 'Acknowledge' }}
                </UButton>
                <div v-else-if="hasResetFailure(alert.id)" class="space-y-2">
                  <p class="rounded-md border border-amber-300 bg-amber-50 p-3 text-sm font-medium leading-5 text-amber-900 dark:border-amber-700/70 dark:bg-amber-950/40 dark:text-amber-200">
                    {{ resetFailureMessage }}
                  </p>
                  <UButton
                    type="button"
                    color="amber"
                    variant="soft"
                    size="sm"
                    block
                    icon="i-heroicons-arrow-path"
                    :loading="isActionPending(alert.id)"
                    :disabled="isActionPending(alert.id)"
                    @click="openAcknowledgment(alert, 'retry')"
                  >
                    {{ isActionPending(alert.id) ? 'Retrying reset…' : 'Retry Reset' }}
                  </UButton>
                </div>
                <p
                  v-if="actionErrors[alert.id]"
                  class="text-sm font-medium text-red-600 dark:text-red-300"
                  role="alert"
                >
                  {{ actionErrors[alert.id] }}
                </p>
              </div>
            </li>
          </ul>
        </div>

        <div v-else class="monitor-panel">
          <AppEmptyState
            :icon="activeTab === 'open'
              ? 'i-heroicons-bell-slash'
              : 'i-heroicons-check-badge'"
            :title="emptyTitle"
            :description="emptyDescription"
          >
            <template v-if="deviceFilterLabel" #actions>
              <UButton type="button" color="gray" variant="outline" @click="clearDeviceFilter">
                Clear Device focus
              </UButton>
            </template>
            <template v-else-if="selectedDatacenterName" #actions>
              <UButton type="button" color="gray" variant="outline" @click="clearDatacenterFilter">
                Clear Datacenter filter
              </UButton>
            </template>
          </AppEmptyState>
        </div>
      </template>
    </div>

    <UModal v-model="mobileFilterOpen" aria-label="Filter Alerts by Datacenter">
      <UCard class="max-w-md" :ui="{ background: 'bg-white dark:bg-[#101827]' }">
        <template #header>
          <h2 class="text-base font-semibold">Filter by Datacenter</h2>
        </template>
        <UFormGroup label="Datacenter" name="mobile-alert-datacenter-filter">
          <USelect v-model="mobileFilterDraft" :options="datacenterOptions" />
        </UFormGroup>
        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="ghost" @click="cancelMobileFilters">Cancel</UButton>
            <UButton @click="applyMobileFilters">Apply filter</UButton>
          </div>
        </template>
      </UCard>
    </UModal>

    <ConfirmDialog
      v-model:open="acknowledgeDialogOpen"
      :title="acknowledgeTitle"
      :description="acknowledgeDescription"
      :confirm-label="acknowledgeLabel"
      :loading="acknowledgeLoading"
      @confirm="submitAcknowledgment"
    />
  </div>
</template>
