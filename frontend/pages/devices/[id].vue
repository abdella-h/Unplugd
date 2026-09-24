<script setup lang="ts">
import type { Device, DeviceState } from '~/types/api'
import { errorDetail } from '~/composables/useApi'

definePageMeta({ title: 'Device detail' })

const route = useRoute()
const auth = useAuth()
const workspace = useWorkspace()
const { apiFetch } = useApi()
const toast = useToast()

const device = ref<Device | null>(null)
const hasLoaded = ref(false)
const loading = ref(true)
const refreshing = ref(false)
let requestSequence = 0
const loadError = ref<string | null>(null)
const loadStatus = ref<number | null>(null)
const metadataError = ref<string | null>(null)
const lastFetchedAt = ref<number | null>(null)
const isInitialLoading = computed(() => !hasLoaded.value && loading.value)

const stateChoices: Array<{ state: DeviceState; label: string; description: string }> = [
  { state: 'ok', label: 'OK', description: 'Reported as OK' },
  { state: 'warning', label: 'Warning', description: 'Reported as needing attention' },
  { state: 'alert', label: 'Alert', description: 'Reported as requiring action' },
]

const deviceId = computed<number | null>(() => {
  const rawId = Array.isArray(route.params.id) ? route.params.id[0] : route.params.id
  if (rawId == null) return null
  const parsedId = Number(rawId)
  return Number.isInteger(parsedId) && parsedId > 0 ? parsedId : null
})

const isForbidden = computed(() => loadStatus.value === 403)
const isNotFound = computed(() => loadStatus.value === 404)
const detailErrorTitle = computed(() => {
  if (isForbidden.value) return 'Device access unavailable'
  if (isNotFound.value) return 'Device not found'
  return 'Device unavailable'
})
const detailErrorDescription = computed(() => {
  if (isForbidden.value) return 'This Device is outside your authorized scope, or your account cannot view it.'
  if (isNotFound.value) return 'This Device does not exist or is no longer available.'
  return loadError.value ?? 'The Device record could not be loaded.'
})
const detailErrorIcon = computed(() => {
  if (isForbidden.value) return 'i-heroicons-lock-closed'
  if (isNotFound.value) return 'i-heroicons-magnifying-glass'
  return 'i-heroicons-exclamation-triangle'
})
const datacenterName = computed(() =>
  device.value ? workspace.datacenterName(device.value.datacenter_id) : '',
)

function statusFromError(error: unknown): number | null {
  const status = (error as { response?: { status?: number } } | null)?.response?.status
  return typeof status === 'number' ? status : null
}

function formatTimestamp(value: string | null | undefined): string {
  if (!value) return 'Not recorded'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'Not recorded'
  return date.toLocaleString([], {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function formatFetchTime(timestamp: number | null): string {
  if (!timestamp) return 'Not loaded yet'
  return `Updated ${new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`
}

async function load() {
  const sequence = ++requestSequence
  const requestedId = deviceId.value
  if (!requestedId) {
    loadStatus.value = 404
    loadError.value = 'The Device link does not contain a valid Device ID.'
    loading.value = false
    refreshing.value = false
    return
  }

  const firstLoad = !hasLoaded.value
  if (firstLoad) loading.value = true
  else refreshing.value = true
  loadError.value = null
  loadStatus.value = null

  try {
    const loadedDevice = await apiFetch<Device>(`/api/devices/devices/${requestedId}`)
    if (sequence !== requestSequence || deviceId.value !== requestedId) return
    device.value = loadedDevice
    hasLoaded.value = true
    lastFetchedAt.value = Date.now()
    workspace.markFresh()

    const metadataLoaded = await workspace.loadDatacenters()
    if (metadataLoaded) {
      metadataError.value = null
    } else {
      metadataError.value = 'Datacenter name could not be refreshed'
    }
  } catch (error) {
    if (sequence !== requestSequence || deviceId.value !== requestedId) return
    loadStatus.value = statusFromError(error)
    loadError.value = errorDetail(error, 'The Device record could not be loaded')
    workspace.markStale()
  } finally {
    if (sequence === requestSequence) {
      loading.value = false
      refreshing.value = false
    }
  }
}

const stateReportOpen = ref(false)
const stateReportValue = ref<DeviceState>('ok')
const stateReportSaving = ref(false)
const stateReportError = ref<string | null>(null)

function openStateReport() {
  if (!device.value || stateReportSaving.value) return
  stateReportValue.value = device.value.state
  stateReportError.value = null
  stateReportOpen.value = true
}

function closeStateReport() {
  if (!stateReportSaving.value) stateReportOpen.value = false
}

async function submitStateReport() {
  const currentDevice = device.value
  if (!currentDevice || stateReportSaving.value) return
  stateReportSaving.value = true
  stateReportError.value = null
  try {
    const updated = await apiFetch<Device>(
      `/api/devices/devices/${currentDevice.id}/state`,
      { method: 'PUT', body: { state: stateReportValue.value } },
    )
    if (device.value?.id !== currentDevice.id) return
    device.value = updated
    lastFetchedAt.value = Date.now()
    stateReportOpen.value = false
    toast.add({ title: `${updated.name} State reported`, color: 'green' })
  } catch (error) {
    if (device.value?.id !== currentDevice.id) return
    stateReportError.value = errorDetail(error, 'The State could not be reported')
  } finally {
    if (device.value?.id === currentDevice.id) stateReportSaving.value = false
  }
}

const editOpen = ref(false)
const editSaving = ref(false)
const editError = ref<string | null>(null)
const editForm = reactive({
  name: '',
  type: '',
  description: '',
  serial_number: '',
})

function openEdit() {
  if (!auth.isAdmin.value || !device.value) return
  Object.assign(editForm, {
    name: device.value.name,
    type: device.value.type,
    description: device.value.description ?? '',
    serial_number: device.value.serial_number ?? '',
  })
  editError.value = null
  editOpen.value = true
}

function closeEdit() {
  if (!editSaving.value) editOpen.value = false
}

async function saveEdit() {
  const currentDevice = device.value
  if (!currentDevice || !auth.isAdmin.value || editSaving.value) return
  const name = editForm.name.trim()
  const type = editForm.type.trim()
  if (!name || !type) {
    editError.value = 'Name and type are required.'
    return
  }

  editSaving.value = true
  editError.value = null
  try {
    const updated = await apiFetch<Device>(`/api/devices/devices/${currentDevice.id}`, {
      method: 'PATCH',
      body: {
        name,
        type,
        description: editForm.description.trim() || null,
        serial_number: editForm.serial_number.trim() || null,
      },
    })
    if (device.value?.id !== currentDevice.id) return
    device.value = updated
    lastFetchedAt.value = Date.now()
    editOpen.value = false
    toast.add({ title: `${updated.name} updated`, color: 'green' })
  } catch (error) {
    if (device.value?.id !== currentDevice.id) return
    editError.value = errorDetail(error, 'The Device could not be updated')
  } finally {
    if (device.value?.id === currentDevice.id) editSaving.value = false
  }
}

watch(deviceId, () => {
  requestSequence += 1
  device.value = null
  hasLoaded.value = false
  loading.value = true
  refreshing.value = false
  stateReportOpen.value = false
  editOpen.value = false
  stateReportSaving.value = false
  editSaving.value = false
  stateReportError.value = null
  editError.value = null
  void load()
})

watch(workspace.generation, () => {
  requestSequence += 1
  device.value = null
  hasLoaded.value = false
  loading.value = Boolean(auth.user.value)
  refreshing.value = false
  stateReportOpen.value = false
  editOpen.value = false
  stateReportSaving.value = false
  editSaving.value = false
  if (auth.user.value) void load()
})

onMounted(load)
</script>

<template>
  <div class="space-y-5">
    <AppPageHeader
      :title="device?.name ?? 'Device detail'"
      :description="device ? `Device #${device.id} · ${datacenterName}` : 'Review the available inventory record and report its current human-reported State.'"
    >
      <template #actions>
        <div class="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
          <span v-if="refreshing" role="status">Refreshing record…</span>
          <span v-else>{{ formatFetchTime(lastFetchedAt) }}</span>
        </div>
        <UButton to="/devices" icon="i-heroicons-arrow-left" color="gray" variant="outline">Back to devices</UButton>
        <UButton
          v-if="auth.isAdmin.value && device"
          icon="i-heroicons-pencil-square"
          @click="openEdit"
        >
          Edit device
        </UButton>
      </template>
    </AppPageHeader>

    <div
      v-if="isInitialLoading"
      class="monitor-panel overflow-hidden"
      aria-label="Loading Device record"
      role="status"
      aria-busy="true"
    >
      <span class="sr-only">Loading Device record</span>
      <div class="grid gap-4 p-5 sm:grid-cols-2">
        <div class="space-y-3">
          <div class="monitor-skeleton h-5 w-1/2 rounded" />
          <div class="monitor-skeleton h-4 w-3/4 rounded" />
          <div class="monitor-skeleton h-4 w-1/3 rounded" />
        </div>
        <div class="space-y-3">
          <div class="monitor-skeleton h-5 w-1/2 rounded" />
          <div class="monitor-skeleton h-4 w-2/3 rounded" />
          <div class="monitor-skeleton h-4 w-1/2 rounded" />
        </div>
      </div>
    </div>

    <div
      v-else-if="loadError && !hasLoaded"
      class="monitor-panel flex min-h-72 flex-col items-center justify-center px-6 py-12 text-center"
      role="alert"
    >
      <div
        class="flex h-14 w-14 items-center justify-center rounded-2xl"
        :class="isForbidden ? 'bg-amber-50 text-amber-700 dark:bg-amber-950/50 dark:text-amber-300' : 'bg-red-50 text-red-700 dark:bg-red-950/50 dark:text-red-300'"
      >
        <UIcon :name="detailErrorIcon" class="h-7 w-7" />
      </div>
      <h2 class="mt-5 text-lg font-semibold">{{ detailErrorTitle }}</h2>
      <p class="mt-2 max-w-md text-sm text-slate-500 dark:text-slate-400">{{ detailErrorDescription }}</p>
      <div class="mt-5 flex flex-wrap justify-center gap-2">
        <UButton to="/devices" color="gray" variant="outline">Back to devices</UButton>
        <UButton v-if="!isForbidden && !isNotFound" :loading="refreshing" @click="load">Retry</UButton>
      </div>
    </div>

    <template v-else-if="hasLoaded && device">
      <UAlert
        v-if="loadError"
        color="amber"
        variant="subtle"
        title="Device refresh failed"
        :description="`${loadError} Showing the last successful record load.`"
      >
        <template #actions>
          <UButton size="xs" color="amber" variant="ghost" :loading="refreshing" @click="load">Retry</UButton>
        </template>
      </UAlert>
      <UAlert
        v-if="metadataError"
        color="amber"
        variant="subtle"
        title="Datacenter name may be incomplete"
        :description="`${metadataError} The Device ID remains visible in the record.`"
      />

      <div class="grid gap-4 lg:grid-cols-[minmax(0,1.35fr)_minmax(280px,0.65fr)]">
        <UCard class="monitor-panel" :ui="{ background: 'bg-white dark:bg-[#101827]' }">
          <template #header>
            <div class="flex items-center gap-3">
              <div class="flex h-9 w-9 items-center justify-center rounded-lg bg-cyan-50 text-cyan-700 dark:bg-cyan-950/50 dark:text-cyan-300">
                <UIcon name="i-heroicons-cpu-chip" class="h-5 w-5" />
              </div>
              <div>
                <h2 class="text-base font-semibold">Device identity</h2>
                <p class="text-xs text-slate-500 dark:text-slate-400">Inventory record #{{ device.id }}</p>
              </div>
            </div>
          </template>
          <dl class="grid gap-5 sm:grid-cols-2">
            <div class="sm:col-span-2">
              <dt class="text-xs font-medium uppercase tracking-[0.08em] text-slate-500 dark:text-slate-400">Name</dt>
              <dd class="mt-1 text-lg font-semibold">{{ device.name }}</dd>
            </div>
            <div>
              <dt class="text-xs font-medium uppercase tracking-[0.08em] text-slate-500 dark:text-slate-400">Datacenter</dt>
              <dd class="mt-1 flex items-center gap-2 font-medium">
                <UIcon name="i-heroicons-building-office-2" class="h-4 w-4 text-slate-400" />
                {{ datacenterName }}
              </dd>
            </div>
            <div>
              <dt class="text-xs font-medium uppercase tracking-[0.08em] text-slate-500 dark:text-slate-400">Type</dt>
              <dd class="mt-1 font-medium">{{ device.type }}</dd>
            </div>
            <div class="sm:col-span-2">
              <dt class="text-xs font-medium uppercase tracking-[0.08em] text-slate-500 dark:text-slate-400">Serial number</dt>
              <dd class="mt-1 font-medium">{{ device.serial_number ?? 'Not recorded' }}</dd>
            </div>
          </dl>
        </UCard>

        <UCard class="monitor-panel" :ui="{ background: 'bg-white dark:bg-[#101827]' }">
          <template #header>
            <div>
              <h2 class="text-base font-semibold">Current State</h2>
              <p class="mt-1 text-xs text-slate-500 dark:text-slate-400">Last recorded human report</p>
            </div>
          </template>
          <div class="flex flex-col items-start gap-4">
            <StateBadge :state="device.state" />
            <p class="text-sm text-slate-500 dark:text-slate-400">
              This is the current State known to Unplugd. It is not a telemetry or availability reading.
            </p>
            <UButton icon="i-heroicons-clipboard-pencil" class="w-full justify-center" @click="openStateReport">Report State</UButton>
          </div>
        </UCard>
      </div>

      <UCard class="monitor-panel" :ui="{ background: 'bg-white dark:bg-[#101827]' }">
        <template #header>
          <div class="flex items-center gap-3">
            <div class="flex h-9 w-9 items-center justify-center rounded-lg bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
              <UIcon name="i-heroicons-document-text" class="h-5 w-5" />
            </div>
            <div>
              <h2 class="text-base font-semibold">Record metadata</h2>
              <p class="text-xs text-slate-500 dark:text-slate-400">Only values returned by the Device API</p>
            </div>
          </div>
        </template>
        <dl class="grid gap-x-8 gap-y-5 sm:grid-cols-2">
          <div class="sm:col-span-2">
            <dt class="text-xs font-medium uppercase tracking-[0.08em] text-slate-500 dark:text-slate-400">Description</dt>
            <dd class="mt-1 whitespace-pre-wrap text-sm leading-6 text-slate-700 dark:text-slate-200">{{ device.description ?? 'No description recorded.' }}</dd>
          </div>
          <div>
            <dt class="text-xs font-medium uppercase tracking-[0.08em] text-slate-500 dark:text-slate-400">Created</dt>
            <dd class="mt-1 text-sm">{{ formatTimestamp(device.created_at) }}</dd>
          </div>
          <div>
            <dt class="text-xs font-medium uppercase tracking-[0.08em] text-slate-500 dark:text-slate-400">Updated</dt>
            <dd class="mt-1 text-sm">{{ formatTimestamp(device.updated_at) }}</dd>
          </div>
        </dl>
      </UCard>
    </template>

    <UModal v-model="stateReportOpen" :prevent-close="stateReportSaving" aria-label="Report Device State">
      <UCard class="max-w-md" :ui="{ background: 'bg-white dark:bg-[#101827]' }">
        <template #header>
          <div class="flex items-start gap-3">
            <div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-cyan-50 text-cyan-700 dark:bg-cyan-950/50 dark:text-cyan-300">
              <UIcon name="i-heroicons-clipboard-pencil" class="h-5 w-5" />
            </div>
            <div>
              <h2 class="text-base font-semibold">Report Device State</h2>
              <p class="mt-1 text-sm text-slate-500 dark:text-slate-400">{{ device?.name ?? 'This Device' }}</p>
            </div>
          </div>
        </template>
        <div class="space-y-4">
          <p class="text-sm text-slate-600 dark:text-slate-300">Choose the State currently reported by an accountable person. This action does not claim telemetry.</p>
          <div class="grid gap-2" role="group" aria-label="Reported Device State">
            <button
              v-for="choice in stateChoices"
              :key="choice.state"
              type="button"
              class="flex min-h-12 items-center justify-between gap-3 rounded-md border px-3 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-700 dark:focus-visible:ring-primary-300"
              :class="stateReportValue === choice.state ? 'border-primary-500 bg-cyan-50/70 dark:bg-cyan-950/30' : 'border-[var(--monitor-border)] hover:bg-[var(--monitor-raised)]'"
              :aria-pressed="stateReportValue === choice.state"
              @click="stateReportValue = choice.state"
            >
              <span class="flex items-center gap-2">
                <StateBadge :state="choice.state" />
                <span class="text-sm font-medium">{{ choice.label }}</span>
              </span>
              <span class="text-xs text-slate-500 dark:text-slate-400">{{ choice.description }}</span>
            </button>
          </div>
          <UAlert v-if="stateReportError" color="red" variant="subtle" :title="stateReportError" />
        </div>
        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="ghost" :disabled="stateReportSaving" @click="closeStateReport">Cancel</UButton>
            <UButton :loading="stateReportSaving" @click="submitStateReport">Report State</UButton>
          </div>
        </template>
      </UCard>
    </UModal>

    <UModal v-model="editOpen" :prevent-close="editSaving" aria-label="Edit Device">
      <UCard class="max-w-xl" :ui="{ background: 'bg-white dark:bg-[#101827]' }">
        <template #header>
          <div class="flex items-start gap-3">
            <div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-cyan-50 text-cyan-700 dark:bg-cyan-950/50 dark:text-cyan-300">
              <UIcon name="i-heroicons-pencil-square" class="h-5 w-5" />
            </div>
            <div>
              <h2 class="text-base font-semibold">Edit Device</h2>
              <p class="mt-1 text-sm text-slate-500 dark:text-slate-400">Update inventory metadata without changing the current State.</p>
            </div>
          </div>
        </template>
        <form class="space-y-4" @submit.prevent="saveEdit">
          <UAlert v-if="editError" color="red" variant="subtle" :title="editError" />
          <div class="grid gap-4 sm:grid-cols-2">
            <UFormGroup label="Name" name="edit-device-name" required>
              <UInput v-model="editForm.name" required maxlength="255" />
            </UFormGroup>
            <UFormGroup label="Type" name="edit-device-type" required>
              <UInput v-model="editForm.type" required maxlength="255" />
            </UFormGroup>
          </div>
          <UFormGroup label="Serial number" name="edit-device-serial-number">
            <UInput v-model="editForm.serial_number" maxlength="255" />
          </UFormGroup>
          <UFormGroup label="Description" name="edit-device-description">
            <UTextarea v-model="editForm.description" :rows="4" maxlength="2000" placeholder="Optional inventory context" />
          </UFormGroup>
          <p class="text-xs text-slate-500 dark:text-slate-400">Current State: {{ device?.state ?? 'Not available' }}. Use Report State to record a new human-reported State.</p>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="ghost" :disabled="editSaving" @click="closeEdit">Cancel</UButton>
            <UButton type="submit" :loading="editSaving">Save changes</UButton>
          </div>
        </form>
      </UCard>
    </UModal>
  </div>
</template>
