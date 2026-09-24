<script setup lang="ts">
import type { Datacenter, Device, DeviceState } from '~/types/api'
import { errorDetail } from '~/composables/useApi'

definePageMeta({ title: 'Devices' })

const auth = useAuth()
const workspace = useWorkspace()
const { apiFetch } = useApi()
const toast = useToast()

type DeviceSort = 'priority' | 'name' | 'datacenter' | 'type' | 'serial' | 'updated'
type StateFilter = 'all' | DeviceState
type DatacenterFilter = 'all' | number

const devices = ref<Device[]>([])
const hasLoaded = ref(false)
const loading = ref(true)
const refreshing = ref(false)
let requestSequence = 0
const loadError = ref<string | null>(null)
const loadStatus = ref<number | null>(null)
const metadataError = ref<string | null>(null)
const lastFetchedAt = ref<number | null>(null)

const search = ref('')
const stateFilter = ref<StateFilter>('all')
const datacenterFilter = ref<DatacenterFilter>('all')
const sortBy = ref<DeviceSort>('priority')
const page = ref(1)
const filtersOpen = ref(false)
const pageSize = 25

const stateChoices: Array<{ state: DeviceState; label: string; description: string }> = [
  { state: 'ok', label: 'OK', description: 'Reported as OK' },
  { state: 'warning', label: 'Warning', description: 'Reported as needing attention' },
  { state: 'alert', label: 'Alert', description: 'Reported as requiring action' },
]
const stateSelectOptions = stateChoices.map((choice) => ({
  label: choice.label,
  value: choice.state,
}))
const stateFilterOptions = [
  { label: 'All States', value: 'all' as StateFilter },
  ...stateSelectOptions,
]
const sortOptions: Array<{ label: string; value: DeviceSort }> = [
  { label: 'Operational priority', value: 'priority' },
  { label: 'Name', value: 'name' },
  { label: 'Datacenter', value: 'datacenter' },
  { label: 'Type', value: 'type' },
  { label: 'Serial number', value: 'serial' },
  { label: 'Recently updated', value: 'updated' },
]

const datacenterOptions = computed<Datacenter[]>(() => {
  const options = new Map<number, Datacenter>()
  for (const datacenter of workspace.datacenters.value) {
    options.set(datacenter.id, datacenter)
  }
  const scopedDatacenterId = auth.user.value?.dcId
  if (scopedDatacenterId != null && !options.has(scopedDatacenterId)) {
    options.set(scopedDatacenterId, {
      id: scopedDatacenterId,
      name: `Datacenter #${scopedDatacenterId}`,
      location: '',
      created_at: '',
      updated_at: '',
    })
  }
  for (const device of devices.value) {
    if (!options.has(device.datacenter_id)) {
      options.set(device.datacenter_id, {
        id: device.datacenter_id,
        name: `Datacenter #${device.datacenter_id}`,
        location: '',
        created_at: '',
        updated_at: '',
      })
    }
  }
  return [...options.values()].sort((left, right) => left.name.localeCompare(right.name))
})

const datacenterFilterOptions = computed(() => [
  { label: 'All datacenters', value: 'all' as DatacenterFilter },
  ...datacenterOptions.value.map((datacenter) => ({
    label: datacenter.name,
    value: datacenter.id as DatacenterFilter,
  })),
])

const statePriority: Record<DeviceState, number> = {
  alert: 0,
  warning: 1,
  ok: 2,
}

const filteredDevices = computed(() => {
  const query = search.value.trim().toLowerCase()
  const matching = devices.value.filter((device) => {
    const matchesQuery =
      !query ||
      [device.name, device.type, device.serial_number ?? ''].some((value) =>
        value.toLowerCase().includes(query),
      )
    const matchesState = stateFilter.value === 'all' || device.state === stateFilter.value
    const matchesDatacenter =
      datacenterFilter.value === 'all' || device.datacenter_id === datacenterFilter.value
    return matchesQuery && matchesState && matchesDatacenter
  })

  return matching.sort((left, right) => {
    let comparison = 0
    if (sortBy.value === 'priority') {
      comparison = statePriority[left.state] - statePriority[right.state]
    } else if (sortBy.value === 'name') {
      comparison = left.name.localeCompare(right.name, undefined, { sensitivity: 'base' })
    } else if (sortBy.value === 'datacenter') {
      comparison = datacenterName(left.datacenter_id).localeCompare(
        datacenterName(right.datacenter_id),
        undefined,
        { sensitivity: 'base' },
      )
    } else if (sortBy.value === 'type') {
      comparison = left.type.localeCompare(right.type, undefined, { sensitivity: 'base' })
    } else if (sortBy.value === 'serial') {
      comparison = (left.serial_number ?? '').localeCompare(right.serial_number ?? '', undefined, {
        sensitivity: 'base',
      })
    } else {
      comparison = Date.parse(right.updated_at ?? '') - Date.parse(left.updated_at ?? '')
    }
    return comparison || left.name.localeCompare(right.name, undefined, { sensitivity: 'base' })
  })
})

const pageCount = computed(() => Math.max(1, Math.ceil(filteredDevices.value.length / pageSize)))
const pagedDevices = computed(() => {
  const start = (page.value - 1) * pageSize
  return filteredDevices.value.slice(start, start + pageSize)
})
const pageStart = computed(() =>
  filteredDevices.value.length === 0 ? 0 : (page.value - 1) * pageSize + 1,
)
const pageEnd = computed(() =>
  Math.min(page.value * pageSize, filteredDevices.value.length),
)
const hasActiveFilters = computed(
  () =>
    search.value.trim().length > 0 ||
    stateFilter.value !== 'all' ||
    datacenterFilter.value !== 'all',
)
const activeFilterCount = computed(() => {
  let count = 0
  if (search.value.trim()) count += 1
  if (stateFilter.value !== 'all') count += 1
  if (datacenterFilter.value !== 'all') count += 1
  return count
})
const stateCounts = computed(() => ({
  ok: devices.value.filter((device) => device.state === 'ok').length,
  warning: devices.value.filter((device) => device.state === 'warning').length,
  alert: devices.value.filter((device) => device.state === 'alert').length,
}))
const isInitialLoading = computed(() => !hasLoaded.value && loading.value)
const isInventoryForbidden = computed(() => loadStatus.value === 403)

watch([search, stateFilter, datacenterFilter, sortBy], () => {
  page.value = 1
})
watch(
  () => filteredDevices.value.length,
  (length) => {
    if (page.value > Math.max(1, Math.ceil(length / pageSize))) page.value = Math.max(1, Math.ceil(length / pageSize))
  },
)

function datacenterName(id: number): string {
  return workspace.datacenters.value.find((datacenter) => datacenter.id === id)?.name ?? `Datacenter #${id}`
}

function statusFromError(error: unknown): number | null {
  const status = (error as { response?: { status?: number } } | null)?.response?.status
  return typeof status === 'number' ? status : null
}

function formatFetchTime(timestamp: number | null): string {
  if (!timestamp) return 'Not loaded yet'
  return `Updated ${new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`
}

async function load() {
  const sequence = ++requestSequence
  const firstLoad = !hasLoaded.value
  if (firstLoad) loading.value = true
  else refreshing.value = true
  loadError.value = null
  loadStatus.value = null

  try {
    const loadedDevices = await apiFetch<Device[]>('/api/devices/devices')
    if (sequence !== requestSequence) return
    devices.value = loadedDevices
    hasLoaded.value = true
    lastFetchedAt.value = Date.now()
    workspace.markFresh()

    const metadataLoaded = await workspace.loadDatacenters()
    if (sequence !== requestSequence) return
    if (metadataLoaded) {
      metadataError.value = null
    } else {
      metadataError.value = 'Datacenter names could not be refreshed'
    }
  } catch (error) {
    if (sequence !== requestSequence) return
    loadStatus.value = statusFromError(error)
    loadError.value = errorDetail(error, 'The Device inventory could not be loaded')
    workspace.markStale()
  } finally {
    if (sequence === requestSequence) {
      loading.value = false
      refreshing.value = false
    }
  }
}

function clearFilters() {
  search.value = ''
  stateFilter.value = 'all'
  datacenterFilter.value = 'all'
}

function setPage(nextPage: number) {
  page.value = Math.min(Math.max(nextPage, 1), pageCount.value)
}

const statePending = ref<Record<number, boolean>>({})
const stateErrors = ref<Record<number, string>>({})
const stateReportOpen = ref(false)
const stateReportDevice = ref<Device | null>(null)
const stateReportValue = ref<DeviceState>('ok')
const stateReportSaving = ref(false)
const stateReportError = ref<string | null>(null)

function isStatePending(deviceId: number): boolean {
  return statePending.value[deviceId] === true
}

function stateError(deviceId: number): string | null {
  return stateErrors.value[deviceId] ?? null
}

function openStateReport(device: Device) {
  if (isStatePending(device.id)) return
  stateReportDevice.value = device
  stateReportValue.value = device.state
  stateReportError.value = null
  stateReportOpen.value = true
}

function closeStateReport() {
  if (!stateReportSaving.value) stateReportOpen.value = false
}

async function submitStateReport() {
  const device = stateReportDevice.value
  if (!device || stateReportSaving.value) return
  stateReportSaving.value = true
  stateReportError.value = null
  statePending.value = { ...statePending.value, [device.id]: true }
  delete stateErrors.value[device.id]

  try {
    const updated = await apiFetch<Device>(
      `/api/devices/devices/${device.id}/state`,
      { method: 'PUT', body: { state: stateReportValue.value } },
    )
    const index = devices.value.findIndex((item) => item.id === updated.id)
    if (index >= 0) devices.value.splice(index, 1, updated)
    if (stateReportDevice.value?.id === updated.id) stateReportDevice.value = updated
    stateReportOpen.value = false
    toast.add({ title: `${updated.name} State reported`, color: 'green' })
  } catch (error) {
    const message = errorDetail(error, 'The State could not be reported')
    stateReportError.value = message
    stateErrors.value = { ...stateErrors.value, [device.id]: message }
    toast.add({ title: message, color: 'red' })
  } finally {
    const pending = { ...statePending.value }
    delete pending[device.id]
    statePending.value = pending
    stateReportSaving.value = false
  }
}

const deviceModalOpen = ref(false)
const editingDevice = ref<Device | null>(null)
const deviceSaving = ref(false)
const deviceFormError = ref<string | null>(null)
const deviceForm = reactive({
  name: '',
  datacenter_id: undefined as number | undefined,
  type: '',
  description: '',
  serial_number: '',
  state: 'ok' as DeviceState,
})

function openCreate() {
  if (!auth.isAdmin.value) return
  editingDevice.value = null
  Object.assign(deviceForm, {
    name: '',
    datacenter_id: auth.user.value?.dcId ?? datacenterOptions.value[0]?.id,
    type: '',
    description: '',
    serial_number: '',
    state: 'ok',
  })
  deviceFormError.value = null
  deviceModalOpen.value = true
}

function openEdit(device: Device) {
  if (!auth.isAdmin.value) return
  editingDevice.value = device
  Object.assign(deviceForm, {
    name: device.name,
    datacenter_id: device.datacenter_id,
    type: device.type,
    description: device.description ?? '',
    serial_number: device.serial_number ?? '',
    state: device.state,
  })
  deviceFormError.value = null
  deviceModalOpen.value = true
}

function closeDeviceModal() {
  if (!deviceSaving.value) deviceModalOpen.value = false
}

async function saveDevice() {
  if (!auth.isAdmin.value || deviceSaving.value) return
  const name = deviceForm.name.trim()
  const type = deviceForm.type.trim()
  const description = deviceForm.description.trim() || null
  const serialNumber = deviceForm.serial_number.trim() || null
  const datacenterId = deviceForm.datacenter_id

  if (!name || !type) {
    deviceFormError.value = 'Name and type are required.'
    return
  }
  if (!editingDevice.value && datacenterId == null) {
    deviceFormError.value = 'Choose a Datacenter before saving.'
    return
  }

  deviceSaving.value = true
  deviceFormError.value = null
  try {
    if (editingDevice.value) {
      const updated = await apiFetch<Device>(
        `/api/devices/devices/${editingDevice.value.id}`,
        {
          method: 'PATCH',
          body: {
            name,
            type,
            description,
            serial_number: serialNumber,
          },
        },
      )
      const index = devices.value.findIndex((item) => item.id === updated.id)
      if (index >= 0) devices.value.splice(index, 1, updated)
      toast.add({ title: `${updated.name} updated`, color: 'green' })
    } else {
      const created = await apiFetch<Device>('/api/devices/devices', {
        method: 'POST',
        body: {
          name,
          datacenter_id: datacenterId,
          type,
          description,
          serial_number: serialNumber,
          state: deviceForm.state,
        },
      })
      devices.value = [...devices.value, created]
      toast.add({ title: `${created.name} added`, color: 'green' })
    }
    deviceModalOpen.value = false
  } catch (error) {
    deviceFormError.value = errorDetail(error, 'The Device could not be saved')
  } finally {
    deviceSaving.value = false
  }
}

const deleteOpen = ref(false)
const deleteTarget = ref<Device | null>(null)
const deleteSaving = ref(false)
const deleteDescription = computed(() =>
  deleteTarget.value
    ? `Delete “${deleteTarget.value.name}”? This removes the Device record and cannot be undone.`
    : 'Delete this Device? This action cannot be undone.',
)

function openDelete(device: Device) {
  if (!auth.isAdmin.value) return
  deleteTarget.value = device
  deleteOpen.value = true
}

async function confirmDelete() {
  const device = deleteTarget.value
  if (!device || deleteSaving.value) return
  deleteSaving.value = true
  try {
    await apiFetch<unknown>(`/api/devices/devices/${device.id}`, { method: 'DELETE' })
    devices.value = devices.value.filter((item) => item.id !== device.id)
    deleteOpen.value = false
    deleteTarget.value = null
    toast.add({ title: `${device.name} deleted`, color: 'green' })
  } catch (error) {
    toast.add({ title: errorDetail(error, 'The Device could not be deleted'), color: 'red' })
  } finally {
    deleteSaving.value = false
  }
}

const inviteOpen = ref(false)
const inviteSaving = ref(false)
const inviteError = ref<string | null>(null)
const inviteCopyError = ref<string | null>(null)
const inviteLink = ref<string | null>(null)
const inviteForm = reactive({
  email: '',
  datacenter_id: undefined as number | undefined,
})

const absoluteInviteLink = computed(() => {
  if (!inviteLink.value) return ''
  if (!import.meta.client) return inviteLink.value
  return new URL(inviteLink.value, window.location.origin).toString()
})

function openInvite() {
  if (!auth.isAdmin.value) return
  Object.assign(inviteForm, {
    email: '',
    datacenter_id: auth.user.value?.dcId ?? datacenterOptions.value[0]?.id,
  })
  inviteLink.value = null
  inviteError.value = null
  inviteCopyError.value = null
  inviteOpen.value = true
}

function closeInvite() {
  if (!inviteSaving.value) inviteOpen.value = false
}

async function sendInvite() {
  if (!auth.isAdmin.value || inviteSaving.value) return
  const email = inviteForm.email.trim()
  if (!email) {
    inviteError.value = 'Enter an email address.'
    return
  }
  if (inviteForm.datacenter_id == null) {
    inviteError.value = 'Choose a Datacenter before sending the invite.'
    return
  }

  inviteSaving.value = true
  inviteError.value = null
  inviteCopyError.value = null
  try {
    const response = await apiFetch<{ invite_link: string }>(
      '/api/auth/register/operator/invite',
      {
        method: 'POST',
        body: { email, datacenter_id: inviteForm.datacenter_id },
      },
    )
    inviteLink.value = response.invite_link
  } catch (error) {
    inviteError.value = errorDetail(error, 'The invite could not be created')
  } finally {
    inviteSaving.value = false
  }
}

async function copyInviteLink() {
  const value = absoluteInviteLink.value
  if (!value) return
  inviteCopyError.value = null
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(value)
    } else {
      const input = document.createElement('textarea')
      input.value = value
      input.setAttribute('readonly', '')
      input.style.position = 'fixed'
      input.style.opacity = '0'
      document.body.appendChild(input)
      input.select()
      const copied = document.execCommand('copy')
      document.body.removeChild(input)
      if (!copied) throw new Error('Copy failed')
    }
    toast.add({ title: 'Invite link copied', color: 'green' })
  } catch {
    inviteCopyError.value = 'The link could not be copied automatically. Copy the link manually.'
  }
}

watch(workspace.generation, () => {
  requestSequence += 1
  devices.value = []
  hasLoaded.value = false
  loading.value = Boolean(auth.user.value)
  refreshing.value = false
  loadError.value = null
  loadStatus.value = null
  metadataError.value = null
  statePending.value = {}
  stateErrors.value = {}
  stateReportOpen.value = false
  stateReportSaving.value = false
  deviceModalOpen.value = false
  deviceSaving.value = false
  inviteOpen.value = false
  inviteSaving.value = false
  deleteOpen.value = false
  deleteTarget.value = null
  deleteSaving.value = false
  search.value = ''
  stateFilter.value = 'all'
  datacenterFilter.value = 'all'
  sortBy.value = 'priority'
  page.value = 1
  if (auth.user.value) void load()
})

onMounted(load)
</script>

<template>
  <div class="space-y-5">
    <AppPageHeader
      title="Devices"
      description="Search, filter, and investigate the human-reported State of every Device in your authorized scope."
    >
      <template #actions>
        <div class="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
          <span v-if="refreshing" role="status">Refreshing inventory…</span>
          <span v-else>{{ formatFetchTime(lastFetchedAt) }}</span>
        </div>
        <UButton
          icon="i-heroicons-arrow-path"
          color="gray"
          variant="outline"
          :loading="refreshing"
          @click="load"
        >
          Refresh
        </UButton>
        <template v-if="auth.isAdmin.value">
          <UButton icon="i-heroicons-envelope" color="gray" variant="outline" @click="openInvite">
            Invite operator
          </UButton>
          <UButton icon="i-heroicons-plus" @click="openCreate">Add device</UButton>
        </template>
      </template>
    </AppPageHeader>

    <section v-if="hasLoaded" class="monitor-panel p-4 sm:p-5" aria-labelledby="reported-states-heading">
      <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 id="reported-states-heading" class="text-base font-semibold">Reported States</h2>
          <p class="mt-1 text-sm text-slate-500 dark:text-slate-400">
            {{ devices.length }} Device{{ devices.length === 1 ? '' : 's' }} in the current authorized scope
          </p>
        </div>
        <div class="flex flex-wrap items-center gap-3 text-sm">
          <span class="tabular-nums text-slate-500 dark:text-slate-400">{{ stateCounts.alert }} alert</span>
          <span class="tabular-nums text-slate-500 dark:text-slate-400">{{ stateCounts.warning }} warning</span>
          <span class="tabular-nums text-slate-500 dark:text-slate-400">{{ stateCounts.ok }} ok</span>
        </div>
      </div>
      <div class="mt-5">
        <StateBar
          :ok="stateCounts.ok"
          :warning="stateCounts.warning"
          :alert="stateCounts.alert"
        />
      </div>
    </section>

    <section class="monitor-panel p-4" aria-label="Device inventory controls">
      <div class="flex flex-col gap-3 lg:flex-row lg:items-end">
        <UFormGroup class="min-w-0 flex-1" label="Search inventory" name="device-search">
          <UInput
            v-model="search"
            icon="i-heroicons-magnifying-glass"
            placeholder="Search by name, type, or serial number"
            autocomplete="off"
            aria-label="Search Devices by name, type, or serial number"
          />
        </UFormGroup>
        <div class="hidden flex-col gap-3 xl:flex xl:flex-row">
          <UFormGroup class="w-48" label="State" name="state-filter">
            <USelect v-model="stateFilter" :options="stateFilterOptions" />
          </UFormGroup>
          <UFormGroup v-if="auth.isGlobalAdmin.value" class="w-56" label="Datacenter" name="datacenter-filter">
            <USelect v-model="datacenterFilter" :options="datacenterFilterOptions" />
          </UFormGroup>
          <UFormGroup v-else class="w-56" label="Datacenter" name="datacenter-scope">
            <div class="flex h-9 items-center gap-2 rounded-md border border-[var(--monitor-border)] bg-[var(--monitor-raised)] px-3 text-sm text-slate-600 dark:text-slate-300">
              <UIcon name="i-heroicons-lock-closed" class="h-3.5 w-3.5" />
              <span class="truncate">{{ workspace.scopeLabel.value }}</span>
            </div>
          </UFormGroup>
          <UFormGroup class="w-52" label="Sort by" name="device-sort">
            <USelect v-model="sortBy" :options="sortOptions" />
          </UFormGroup>
        </div>
        <div class="flex items-center gap-2 xl:hidden">
          <UButton
            icon="i-heroicons-funnel"
            color="gray"
            variant="outline"
            class="flex-1"
            @click="filtersOpen = true"
          >
            Filters
            <UBadge v-if="activeFilterCount" color="cyan" variant="subtle" class="ml-1">
              {{ activeFilterCount }}
            </UBadge>
          </UButton>
          <UButton
            icon="i-heroicons-bars-arrow-down"
            color="gray"
            variant="outline"
            aria-label="Change sort order"
            @click="filtersOpen = true"
          />
        </div>
      </div>
      <div v-if="hasActiveFilters" class="mt-3 flex flex-wrap items-center gap-2 text-sm">
        <span class="text-slate-500 dark:text-slate-400">{{ filteredDevices.length }} matching Device{{ filteredDevices.length === 1 ? '' : 's' }}</span>
        <UButton color="gray" variant="ghost" size="xs" @click="clearFilters">Clear filters</UButton>
      </div>
    </section>

    <UAlert
      v-if="metadataError && hasLoaded"
      color="amber"
      variant="subtle"
      title="Datacenter names may be incomplete"
      :description="`${metadataError} Devices remain available using their Datacenter ID.`"
    >
      <template #actions>
        <UButton size="xs" color="amber" variant="ghost" :loading="refreshing" @click="load">Retry names</UButton>
      </template>
    </UAlert>

    <UAlert
      v-if="loadError && hasLoaded"
      color="amber"
      variant="subtle"
      title="Inventory refresh failed"
      :description="`${loadError} Showing the last successful inventory load.`"
    >
      <template #actions>
        <UButton size="xs" color="amber" variant="ghost" :loading="refreshing" @click="load">Retry</UButton>
      </template>
    </UAlert>

    <div
      v-if="isInitialLoading"
      class="monitor-panel overflow-hidden"
      aria-label="Preparing Device inventory"
      role="status"
      aria-busy="true"
    >
      <span class="sr-only">Loading Device inventory</span>
      <div class="border-b border-[var(--monitor-border)] px-4 py-3">
        <div class="monitor-skeleton h-4 w-40 rounded" />
      </div>
      <div class="divide-y divide-[var(--monitor-border)]">
        <div v-for="index in 6" :key="index" class="flex items-center gap-4 px-4 py-4">
          <div class="monitor-skeleton h-9 w-9 rounded-lg" />
          <div class="flex-1 space-y-2">
            <div class="monitor-skeleton h-3.5 w-2/5 rounded" />
            <div class="monitor-skeleton h-3 w-3/5 rounded" />
          </div>
          <div class="monitor-skeleton hidden h-6 w-24 rounded-full sm:block" />
          <div class="monitor-skeleton hidden h-8 w-28 rounded-md sm:block" />
        </div>
      </div>
    </div>

    <div
      v-else-if="loadError && !hasLoaded"
      class="monitor-panel flex min-h-64 flex-col items-center justify-center px-6 py-12 text-center"
      role="alert"
    >
      <div
        class="flex h-14 w-14 items-center justify-center rounded-2xl"
        :class="isInventoryForbidden ? 'bg-amber-50 text-amber-700 dark:bg-amber-950/50 dark:text-amber-300' : 'bg-red-50 text-red-700 dark:bg-red-950/50 dark:text-red-300'"
      >
        <UIcon :name="isInventoryForbidden ? 'i-heroicons-lock-closed' : 'i-heroicons-exclamation-triangle'" class="h-7 w-7" />
      </div>
      <h2 class="mt-5 text-lg font-semibold">
        {{ isInventoryForbidden ? 'Device inventory access unavailable' : 'Inventory could not be loaded' }}
      </h2>
      <p class="mt-2 max-w-md text-sm text-slate-500 dark:text-slate-400">
        {{ isInventoryForbidden ? 'Your account is not authorized to view this Device scope.' : loadError }}
      </p>
      <div class="mt-5 flex flex-wrap justify-center gap-2">
        <UButton v-if="isInventoryForbidden" to="/" color="gray" variant="outline">Return to overview</UButton>
        <UButton v-else :loading="refreshing" @click="load">Retry inventory</UButton>
      </div>
    </div>

    <div
      v-else-if="hasLoaded && filteredDevices.length === 0"
      class="monitor-panel"
    >
      <div class="flex min-h-64 flex-col items-center justify-center px-6 py-12 text-center">
        <div class="flex h-12 w-12 items-center justify-center rounded-xl border border-[var(--monitor-border)] bg-[var(--monitor-raised)] text-slate-500 dark:text-slate-300">
          <UIcon :name="hasActiveFilters ? 'i-heroicons-funnel' : 'i-heroicons-cpu-chip'" class="h-6 w-6" />
        </div>
        <h2 class="mt-4 text-base font-semibold">
          {{ hasActiveFilters ? 'No Devices match these filters' : 'No Devices in this scope' }}
        </h2>
        <p class="mt-1 max-w-md text-sm text-slate-500 dark:text-slate-400">
          {{ hasActiveFilters ? 'Try a different search term or clear the filters to widen the inventory.' : 'Devices added to the authorized Datacenter scope will appear here.' }}
        </p>
        <UButton v-if="hasActiveFilters" class="mt-5" color="gray" variant="outline" @click="clearFilters">Clear filters</UButton>
      </div>
    </div>

    <template v-else>
      <div class="monitor-table hidden overflow-x-auto lg:block">
        <table class="w-full min-w-[700px] text-left">
          <caption class="sr-only">Device inventory</caption>
          <thead class="border-b border-[var(--monitor-border)] bg-[var(--monitor-raised)]">
            <tr>
              <th scope="col" class="px-4 py-3 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500 dark:text-slate-400">Device</th>
              <th scope="col" class="hidden px-4 py-3 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500 dark:text-slate-400 xl:table-cell">Datacenter</th>
              <th scope="col" class="hidden px-4 py-3 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500 dark:text-slate-400 2xl:table-cell">Type</th>
              <th scope="col" class="hidden px-4 py-3 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500 dark:text-slate-400 xl:table-cell">Serial</th>
              <th scope="col" class="px-4 py-3 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500 dark:text-slate-400">State</th>
              <th v-if="auth.isAdmin.value" scope="col" class="px-4 py-3 text-right text-xs font-semibold uppercase tracking-[0.08em] text-slate-500 dark:text-slate-400">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-[var(--monitor-border)]">
            <tr
              v-for="device in pagedDevices"
              :key="device.id"
              class="transition-colors hover:bg-[var(--monitor-raised)] focus-within:bg-[var(--monitor-raised)]"
            >
              <td class="px-4 py-3">
                <NuxtLink
                  :to="`/devices/${device.id}`"
                  class="font-semibold text-slate-900 hover:text-primary-700 dark:text-white dark:hover:text-primary-300"
                  @click.stop
                >
                  {{ device.name }}
                </NuxtLink>
                <span class="mt-1 block text-xs text-slate-500 dark:text-slate-400">#{{ device.id }}</span>
              </td>
              <td class="hidden px-4 py-3 text-slate-600 dark:text-slate-300 xl:table-cell">{{ datacenterName(device.datacenter_id) }}</td>
              <td class="hidden px-4 py-3 text-slate-600 dark:text-slate-300 2xl:table-cell">{{ device.type }}</td>
              <td class="hidden px-4 py-3 text-slate-600 dark:text-slate-300 xl:table-cell">{{ device.serial_number ?? 'Not recorded' }}</td>
              <td class="px-4 py-3" @click.stop @keydown.stop>
                <div class="min-w-[190px]">
                  <div class="flex items-center gap-2">
                    <StateBadge :state="device.state" />
                    <UButton size="xs" color="gray" variant="ghost" @click="openStateReport(device)">Report State</UButton>
                  </div>
                  <p v-if="isStatePending(device.id)" class="mt-1 flex items-center gap-1 text-xs text-slate-500 dark:text-slate-400" role="status">
                    <UIcon name="i-heroicons-arrow-path" class="h-3.5 w-3.5 animate-spin" /> Reporting…
                  </p>
                  <p v-if="stateError(device.id)" class="mt-1 flex items-start gap-1 text-xs text-red-600 dark:text-red-300" role="alert">
                    <UIcon name="i-heroicons-exclamation-circle" class="mt-0.5 h-3.5 w-3.5 shrink-0" /> {{ stateError(device.id) }}
                  </p>
                </div>
              </td>
              <td v-if="auth.isAdmin.value" class="px-4 py-3" @click.stop @keydown.stop>
                <div class="flex justify-end gap-1">
                  <UButton
                    icon="i-heroicons-pencil-square"
                    color="gray"
                    variant="ghost"
                    size="xs"
                    square
                    :aria-label="`Edit ${device.name}`"
                    @click="openEdit(device)"
                  />
                  <UButton
                    icon="i-heroicons-trash"
                    color="red"
                    variant="ghost"
                    size="xs"
                    square
                    :aria-label="`Delete ${device.name}`"
                    @click="openDelete(device)"
                  />
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="space-y-3 lg:hidden">
        <article
          v-for="device in pagedDevices"
          :key="device.id"
          class="monitor-panel p-4"
        >
          <div class="flex items-start justify-between gap-3">
            <div class="min-w-0">
              <NuxtLink :to="`/devices/${device.id}`" class="block truncate text-base font-semibold" @click.stop>
                {{ device.name }}
              </NuxtLink>
              <p class="mt-1 text-xs text-slate-500 dark:text-slate-400">#{{ device.id }} · {{ device.type }}</p>
            </div>
            <StateBadge :state="device.state" />
          </div>
          <dl class="mt-4 grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
            <div class="min-w-0">
              <dt class="text-xs text-slate-500 dark:text-slate-400">Datacenter</dt>
              <dd class="mt-0.5 truncate font-medium">{{ datacenterName(device.datacenter_id) }}</dd>
            </div>
            <div class="min-w-0">
              <dt class="text-xs text-slate-500 dark:text-slate-400">Serial number</dt>
              <dd class="mt-0.5 truncate font-medium">{{ device.serial_number ?? 'Not recorded' }}</dd>
            </div>
          </dl>
          <div class="mt-4 flex flex-wrap items-center gap-2 border-t border-[var(--monitor-border)] pt-3" @click.stop @keydown.stop>
            <UButton size="sm" color="gray" variant="outline" class="min-h-10" @click="openStateReport(device)">Report State</UButton>
            <template v-if="auth.isAdmin.value">
              <UButton size="sm" color="gray" variant="ghost" class="min-h-10" :aria-label="`Edit ${device.name}`" @click="openEdit(device)">
                <UIcon name="i-heroicons-pencil-square" class="h-4 w-4" /> Edit
              </UButton>
              <UButton size="sm" color="red" variant="ghost" class="min-h-10" :aria-label="`Delete ${device.name}`" @click="openDelete(device)">
                <UIcon name="i-heroicons-trash" class="h-4 w-4" /> Delete
              </UButton>
            </template>
            <span v-if="isStatePending(device.id)" class="flex items-center gap-1 text-xs text-slate-500 dark:text-slate-400" role="status">
              <UIcon name="i-heroicons-arrow-path" class="h-3.5 w-3.5 animate-spin" /> Reporting…
            </span>
          </div>
          <p v-if="stateError(device.id)" class="mt-2 flex items-start gap-1 text-xs text-red-600 dark:text-red-300" role="alert">
            <UIcon name="i-heroicons-exclamation-circle" class="mt-0.5 h-3.5 w-3.5 shrink-0" /> {{ stateError(device.id) }}
          </p>
        </article>
      </div>

      <nav class="flex flex-col gap-3 rounded-lg border border-[var(--monitor-border)] bg-[var(--monitor-surface)] px-4 py-3 sm:flex-row sm:items-center sm:justify-between" aria-label="Device inventory pagination">
        <p class="text-sm text-slate-500 dark:text-slate-400">
          Showing <span class="tabular-nums">{{ pageStart }}–{{ pageEnd }}</span> of
          <span class="tabular-nums">{{ filteredDevices.length }}</span> matching Device{{ filteredDevices.length === 1 ? '' : 's' }}
        </p>
        <div class="flex items-center gap-2">
          <UButton
            icon="i-heroicons-chevron-left"
            color="gray"
            variant="outline"
            size="sm"
            square
            aria-label="Previous page"
            :disabled="page === 1"
            @click="setPage(page - 1)"
          />
          <span class="min-w-24 text-center text-sm tabular-nums text-slate-600 dark:text-slate-300">Page {{ page }} of {{ pageCount }}</span>
          <UButton
            icon="i-heroicons-chevron-right"
            color="gray"
            variant="outline"
            size="sm"
            square
            aria-label="Next page"
            :disabled="page === pageCount"
            @click="setPage(page + 1)"
          />
        </div>
      </nav>
    </template>

    <UModal v-model="filtersOpen" aria-label="Device filters">
      <UCard class="max-w-md" :ui="{ background: 'bg-white dark:bg-[#101827]' }">
        <template #header>
          <div class="flex items-start gap-3">
            <div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-cyan-50 text-cyan-700 dark:bg-cyan-950/50 dark:text-cyan-300">
              <UIcon name="i-heroicons-funnel" class="h-5 w-5" />
            </div>
            <div>
              <h2 class="text-base font-semibold">Device filters</h2>
              <p class="mt-1 text-sm text-slate-500 dark:text-slate-400">Narrow the inventory without losing your place.</p>
            </div>
          </div>
        </template>
        <div class="space-y-4">
          <UFormGroup label="State" name="mobile-state-filter">
            <USelect v-model="stateFilter" :options="stateFilterOptions" />
          </UFormGroup>
          <UFormGroup v-if="auth.isGlobalAdmin.value" label="Datacenter" name="mobile-datacenter-filter">
            <USelect v-model="datacenterFilter" :options="datacenterFilterOptions" />
          </UFormGroup>
          <div v-else>
            <p class="mb-1.5 text-sm font-medium">Datacenter scope</p>
            <div class="flex items-center gap-2 rounded-md border border-[var(--monitor-border)] bg-[var(--monitor-raised)] px-3 py-2.5 text-sm text-slate-600 dark:text-slate-300">
              <UIcon name="i-heroicons-lock-closed" class="h-4 w-4" />
              <span>{{ workspace.scopeLabel.value }}</span>
            </div>
          </div>
          <UFormGroup label="Sort by" name="mobile-device-sort">
            <USelect v-model="sortBy" :options="sortOptions" />
          </UFormGroup>
        </div>
        <template #footer>
          <div class="flex justify-between gap-2">
            <UButton v-if="hasActiveFilters" color="gray" variant="ghost" @click="clearFilters">Clear</UButton>
            <span v-else />
            <UButton @click="filtersOpen = false">Done</UButton>
          </div>
        </template>
      </UCard>
    </UModal>

    <UModal v-model="stateReportOpen" :prevent-close="stateReportSaving" aria-label="Report Device State">
      <UCard class="max-w-md" :ui="{ background: 'bg-white dark:bg-[#101827]' }">
        <template #header>
          <div class="flex items-start gap-3">
            <div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-cyan-50 text-cyan-700 dark:bg-cyan-950/50 dark:text-cyan-300">
              <UIcon name="i-heroicons-clipboard-pencil" class="h-5 w-5" />
            </div>
            <div>
              <h2 class="text-base font-semibold">Report Device State</h2>
              <p class="mt-1 text-sm text-slate-500 dark:text-slate-400">
                {{ stateReportDevice?.name ?? 'This Device' }}
              </p>
            </div>
          </div>
        </template>
        <div class="space-y-4">
          <p class="text-sm text-slate-600 dark:text-slate-300">
            Choose the State currently reported by an accountable person. This action does not claim telemetry.
          </p>
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

    <UModal v-model="deviceModalOpen" :prevent-close="deviceSaving" :aria-label="editingDevice ? 'Edit Device' : 'Add Device'">
      <UCard class="max-w-2xl" :ui="{ background: 'bg-white dark:bg-[#101827]' }">
        <template #header>
          <div class="flex items-start gap-3">
            <div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-cyan-50 text-cyan-700 dark:bg-cyan-950/50 dark:text-cyan-300">
              <UIcon :name="editingDevice ? 'i-heroicons-pencil-square' : 'i-heroicons-plus-circle'" class="h-5 w-5" />
            </div>
            <div>
              <h2 class="text-base font-semibold">{{ editingDevice ? 'Edit Device' : 'Add Device' }}</h2>
              <p class="mt-1 text-sm text-slate-500 dark:text-slate-400">
                {{ editingDevice ? 'Update the inventory record without changing its reported State.' : 'Register a Device in an authorized Datacenter.' }}
              </p>
            </div>
          </div>
        </template>
        <form class="space-y-4" @submit.prevent="saveDevice">
          <UAlert v-if="deviceFormError" color="red" variant="subtle" :title="deviceFormError" />
          <div class="grid gap-4 sm:grid-cols-2">
            <UFormGroup label="Name" name="device-name" required>
              <UInput v-model="deviceForm.name" required maxlength="255" />
            </UFormGroup>
            <UFormGroup v-if="!editingDevice" label="Datacenter" name="device-datacenter" required>
              <USelect
                v-model="deviceForm.datacenter_id"
                :options="datacenterFilterOptions.slice(1)"
                :disabled="!auth.isGlobalAdmin.value"
                required
              />
            </UFormGroup>
            <UFormGroup v-else label="Datacenter" name="device-datacenter-readonly">
              <div class="flex h-9 items-center gap-2 rounded-md border border-[var(--monitor-border)] bg-[var(--monitor-raised)] px-3 text-sm text-slate-600 dark:text-slate-300">
                <UIcon name="i-heroicons-lock-closed" class="h-3.5 w-3.5" />
                {{ datacenterName(editingDevice.datacenter_id) }}
              </div>
            </UFormGroup>
            <UFormGroup label="Type" name="device-type" required>
              <UInput v-model="deviceForm.type" required maxlength="255" />
            </UFormGroup>
            <UFormGroup label="Serial number" name="device-serial-number">
              <UInput v-model="deviceForm.serial_number" maxlength="255" />
            </UFormGroup>
            <UFormGroup v-if="!editingDevice" label="Initial State" name="device-initial-state">
              <USelect v-model="deviceForm.state" :options="stateSelectOptions" />
            </UFormGroup>
          </div>
          <UFormGroup label="Description" name="device-description">
            <UTextarea v-model="deviceForm.description" :rows="3" maxlength="2000" placeholder="Optional inventory context" />
          </UFormGroup>
          <p v-if="editingDevice" class="text-xs text-slate-500 dark:text-slate-400">
            Current State: {{ editingDevice.state }}. Use Report State to record a new human-reported State.
          </p>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="ghost" :disabled="deviceSaving" @click="closeDeviceModal">Cancel</UButton>
            <UButton type="submit" :loading="deviceSaving">{{ editingDevice ? 'Save changes' : 'Add Device' }}</UButton>
          </div>
        </form>
      </UCard>
    </UModal>

    <UModal v-model="inviteOpen" :prevent-close="inviteSaving" aria-label="Invite Operator">
      <UCard class="max-w-lg" :ui="{ background: 'bg-white dark:bg-[#101827]' }">
        <template #header>
          <div class="flex items-start gap-3">
            <div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-cyan-50 text-cyan-700 dark:bg-cyan-950/50 dark:text-cyan-300">
              <UIcon name="i-heroicons-envelope" class="h-5 w-5" />
            </div>
            <div>
              <h2 class="text-base font-semibold">Invite an operator</h2>
              <p class="mt-1 text-sm text-slate-500 dark:text-slate-400">Create a time-limited link for a new Operator in the selected Datacenter.</p>
            </div>
          </div>
        </template>
        <div v-if="inviteLink" class="space-y-4">
          <UAlert color="green" variant="subtle" title="Invite created" description="Send this link to the Operator. It expires automatically." />
          <div class="rounded-md border border-[var(--monitor-border)] bg-[var(--monitor-raised)] p-3">
            <code class="block break-all text-sm text-slate-700 dark:text-slate-200">{{ absoluteInviteLink }}</code>
          </div>
          <UAlert v-if="inviteCopyError" color="amber" variant="subtle" :title="inviteCopyError" />
          <div class="flex flex-wrap justify-end gap-2">
            <UButton color="gray" variant="ghost" @click="inviteOpen = false">Close</UButton>
            <UButton icon="i-heroicons-clipboard-document" @click="copyInviteLink">Copy invite link</UButton>
          </div>
        </div>
        <form v-else class="space-y-4" @submit.prevent="sendInvite">
          <UAlert v-if="inviteError" color="red" variant="subtle" :title="inviteError" />
          <UFormGroup label="Email address" name="invite-email" required>
            <UInput v-model="inviteForm.email" type="email" required autocomplete="email" placeholder="operator@example.com" />
          </UFormGroup>
          <UFormGroup label="Datacenter" name="invite-datacenter" required>
            <USelect
              v-model="inviteForm.datacenter_id"
              :options="datacenterFilterOptions.slice(1)"
              :disabled="!auth.isGlobalAdmin.value"
              required
            />
          </UFormGroup>
          <p class="text-xs text-slate-500 dark:text-slate-400">The invite creates an inactive Operator account until the recipient accepts and chooses a username.</p>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="ghost" :disabled="inviteSaving" @click="closeInvite">Cancel</UButton>
            <UButton type="submit" :loading="inviteSaving">Create invite link</UButton>
          </div>
        </form>
      </UCard>
    </UModal>

    <ConfirmDialog
      :open="deleteOpen"
      title="Delete Device"
      :description="deleteDescription"
      confirm-label="Delete Device"
      :loading="deleteSaving"
      danger
      @update:open="deleteOpen = $event"
      @confirm="confirmDelete"
    />
  </div>
</template>
