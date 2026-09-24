<script setup lang="ts">
import type { Datacenter } from '~/types/api'

definePageMeta({ title: 'Datacenters' })

const auth = useAuth()
const workspace = useWorkspace()
const { apiFetch } = useApi()
const toast = useToast()

if (!auth.isGlobalAdmin.value) {
  await navigateTo('/')
}

const datacenters = ref<Datacenter[]>([])
const loading = ref(true)
const hasLoaded = ref(false)
const refreshing = ref(false)
const error = ref<string | null>(null)
const search = ref('')
const sortBy = ref<'name' | 'location' | 'created'>('name')
const modalOpen = ref(false)
const editing = ref<Datacenter | null>(null)
const saving = ref(false)
const formError = ref<string | null>(null)
const form = reactive({ name: '', location: '' })
const deleteOpen = ref(false)
const deleteTarget = ref<Datacenter | null>(null)
const deleteSaving = ref(false)
let requestSequence = 0

const filteredDatacenters = computed(() => {
  const query = search.value.trim().toLowerCase()
  return [...datacenters.value]
    .filter((datacenter) => {
      if (!query) return true
      return [datacenter.name, datacenter.location].some((value) => value.toLowerCase().includes(query))
    })
    .sort((left, right) => {
      if (sortBy.value === 'location') return left.location.localeCompare(right.location)
      if (sortBy.value === 'created') return Date.parse(right.created_at) - Date.parse(left.created_at)
      return left.name.localeCompare(right.name)
    })
})

const hasFilters = computed(() => search.value.trim().length > 0)

async function load() {
  const sequence = ++requestSequence
  const firstLoad = !hasLoaded.value
  if (firstLoad) loading.value = true
  else refreshing.value = true
  error.value = null
  try {
    const metadataLoaded = await workspace.loadDatacenters()
    if (sequence !== requestSequence) return
    if (!metadataLoaded) throw new Error('Datacenters could not be loaded')
    datacenters.value = [...workspace.datacenters.value]
    hasLoaded.value = true
    workspace.markFresh()
  } catch (caught) {
    if (sequence !== requestSequence) return
    error.value = errorDetail(caught, 'Datacenters could not be loaded')
    workspace.markStale()
  } finally {
    if (sequence === requestSequence) {
      loading.value = false
      refreshing.value = false
    }
  }
}

function openCreate() {
  editing.value = null
  Object.assign(form, { name: '', location: '' })
  formError.value = null
  modalOpen.value = true
}

function openEdit(datacenter: Datacenter) {
  editing.value = datacenter
  Object.assign(form, { name: datacenter.name, location: datacenter.location })
  formError.value = null
  modalOpen.value = true
}

async function save() {
  if (saving.value) return
  const name = form.name.trim()
  const location = form.location.trim()
  if (!name || !location) {
    formError.value = 'Name and location are required.'
    return
  }
  const requestGeneration = workspace.generation.value
  saving.value = true
  formError.value = null
  try {
    if (editing.value) {
      const updated = await apiFetch<Datacenter>(`/api/devices/datacenters/${editing.value.id}`, {
        method: 'PATCH',
        body: { name, location },
      })
      if (workspace.generation.value !== requestGeneration) return
      const index = datacenters.value.findIndex((datacenter) => datacenter.id === updated.id)
      if (index >= 0) datacenters.value[index] = updated
      workspace.datacenters.value = [...datacenters.value]
      toast.add({ title: `${updated.name} updated`, color: 'green' })
    } else {
      const created = await apiFetch<Datacenter>('/api/devices/datacenters', {
        method: 'POST',
        body: { name, location },
      })
      if (workspace.generation.value !== requestGeneration) return
      datacenters.value = [...datacenters.value, created]
      workspace.datacenters.value = [...datacenters.value]
      toast.add({ title: `${created.name} added`, color: 'green' })
    }
    modalOpen.value = false
  } catch (caught) {
    if (workspace.generation.value === requestGeneration) {
      formError.value = errorDetail(caught, 'The Datacenter could not be saved')
    }
  } finally {
    if (workspace.generation.value === requestGeneration) saving.value = false
  }
}

function openDelete(datacenter: Datacenter) {
  deleteTarget.value = datacenter
  deleteOpen.value = true
}

async function confirmDelete() {
  const datacenter = deleteTarget.value
  if (!datacenter || deleteSaving.value) return
  const requestGeneration = workspace.generation.value
  deleteSaving.value = true
  try {
    await apiFetch(`/api/devices/datacenters/${datacenter.id}`, { method: 'DELETE' })
    if (workspace.generation.value !== requestGeneration) return
    datacenters.value = datacenters.value.filter((item) => item.id !== datacenter.id)
    workspace.datacenters.value = [...datacenters.value]
    deleteOpen.value = false
    deleteTarget.value = null
    toast.add({ title: `${datacenter.name} deleted`, color: 'green' })
  } catch (caught) {
    if (workspace.generation.value === requestGeneration) {
      toast.add({ title: errorDetail(caught, 'The Datacenter could not be deleted'), color: 'red' })
    }
  } finally {
    if (workspace.generation.value === requestGeneration) deleteSaving.value = false
  }
}

function formatDate(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
}

watch(workspace.generation, () => {
  requestSequence += 1
  datacenters.value = []
  hasLoaded.value = false
  loading.value = Boolean(auth.user.value)
  refreshing.value = false
  error.value = null
  modalOpen.value = false
  deleteOpen.value = false
  deleteTarget.value = null
  saving.value = false
  deleteSaving.value = false
  if (auth.user.value) void load()
})

onMounted(load)
</script>

<template>
  <div class="space-y-5">
    <AppPageHeader
      title="Datacenters"
      description="Manage the facilities that define your operational monitoring scope."
    >
      <template #actions>
        <UButton icon="i-heroicons-arrow-path" color="gray" variant="outline" :loading="refreshing" @click="load">
          Refresh
        </UButton>
        <UButton icon="i-heroicons-plus" @click="openCreate">Add datacenter</UButton>
      </template>
    </AppPageHeader>

    <UAlert v-if="error && hasLoaded" color="amber" variant="subtle" title="Datacenter data is stale" :description="`${error} Showing the last successful load.`">
      <template #actions>
        <UButton size="xs" color="red" variant="soft" @click="load">Retry</UButton>
      </template>
    </UAlert>

    <div v-if="error && !hasLoaded" class="monitor-panel">
      <AppEmptyState
        icon="i-heroicons-exclamation-triangle"
        title="Datacenter inventory unavailable"
        :description="error ?? 'The configured facilities could not be loaded.'"
      >
        <template #actions>
          <UButton color="primary" @click="load">Retry Datacenters</UButton>
        </template>
      </AppEmptyState>
    </div>

    <section class="monitor-panel p-4 sm:p-5" aria-label="Datacenter controls">
      <div class="flex flex-col gap-3 sm:flex-row sm:items-end">
        <UFormGroup class="min-w-0 flex-1" label="Search Datacenters" name="datacenter-search">
          <UInput v-model="search" icon="i-heroicons-magnifying-glass" placeholder="Search by name or location" autocomplete="off" />
        </UFormGroup>
        <UFormGroup class="w-full sm:w-52" label="Sort by" name="datacenter-sort">
          <USelect
            v-model="sortBy"
            :options="[
              { label: 'Name', value: 'name' },
              { label: 'Location', value: 'location' },
              { label: 'Recently created', value: 'created' },
            ]"
          />
        </UFormGroup>
      </div>
      <div v-if="hasFilters" class="mt-3 flex items-center gap-3 text-sm">
        <span class="text-slate-500 dark:text-slate-400">{{ filteredDatacenters.length }} matching Datacenter{{ filteredDatacenters.length === 1 ? '' : 's' }}</span>
        <UButton size="xs" color="gray" variant="ghost" @click="search = ''">Clear search</UButton>
      </div>
    </section>

    <div v-if="loading" class="monitor-panel p-4" aria-label="Loading Datacenters" role="status" aria-busy="true">
      <span class="sr-only">Loading Datacenters</span>
      <div class="space-y-3">
        <div v-for="index in 4" :key="index" class="monitor-skeleton h-14 rounded-lg" />
      </div>
    </div>
    <div v-else-if="hasLoaded && filteredDatacenters.length === 0" class="monitor-panel">
      <AppEmptyState
        :icon="hasFilters ? 'i-heroicons-funnel' : 'i-heroicons-building-office-2'"
        :title="hasFilters ? 'No Datacenters match this search' : 'No Datacenters configured'"
        :description="hasFilters ? 'Clear the search to view all configured facilities.' : 'Add the first facility to begin monitoring Devices.'"
      >
        <template v-if="hasFilters" #actions>
          <UButton color="gray" variant="outline" @click="search = ''">Clear search</UButton>
        </template>
        <template v-else #actions>
          <UButton icon="i-heroicons-plus" @click="openCreate">Add datacenter</UButton>
        </template>
      </AppEmptyState>
    </div>

    <div v-else-if="hasLoaded && filteredDatacenters.length > 0" class="monitor-table hidden overflow-x-auto sm:block">
      <table class="w-full min-w-[720px] text-left">
        <caption class="sr-only">Configured Datacenters</caption>
        <thead class="border-b border-[var(--monitor-border)] bg-[var(--monitor-raised)]">
          <tr>
            <th scope="col" class="px-4 py-3 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500 dark:text-slate-400">Name</th>
            <th scope="col" class="px-4 py-3 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500 dark:text-slate-400">Location</th>
            <th scope="col" class="px-4 py-3 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500 dark:text-slate-400">Created</th>
            <th scope="col" class="px-4 py-3 text-right text-xs font-semibold uppercase tracking-[0.08em] text-slate-500 dark:text-slate-400">Actions</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-[var(--monitor-border)]">
          <tr v-for="datacenter in filteredDatacenters" :key="datacenter.id" class="hover:bg-[var(--monitor-raised)]">
            <td class="px-4 py-3">
              <div class="flex items-center gap-3">
                <div class="flex h-9 w-9 items-center justify-center rounded-lg bg-cyan-50 text-cyan-700 dark:bg-cyan-950/50 dark:text-cyan-300">
                  <UIcon name="i-heroicons-building-office-2" class="h-5 w-5" />
                </div>
                <div>
                  <p class="font-semibold">{{ datacenter.name }}</p>
                  <p class="text-xs text-slate-500 dark:text-slate-400">ID #{{ datacenter.id }}</p>
                </div>
              </div>
            </td>
            <td class="px-4 py-3 text-slate-600 dark:text-slate-300">{{ datacenter.location }}</td>
            <td class="px-4 py-3 text-slate-600 dark:text-slate-300">{{ formatDate(datacenter.created_at) }}</td>
            <td class="px-4 py-3">
              <div class="flex justify-end gap-1">
                <UButton icon="i-heroicons-pencil-square" color="gray" variant="ghost" size="sm" class="h-10 w-10" :aria-label="`Edit ${datacenter.name}`" @click="openEdit(datacenter)" />
                <UButton icon="i-heroicons-trash" color="red" variant="ghost" size="sm" class="h-10 w-10" :aria-label="`Delete ${datacenter.name}`" @click="openDelete(datacenter)" />
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <ul v-if="hasLoaded && !loading && filteredDatacenters.length" class="space-y-3 sm:hidden">
      <li v-for="datacenter in filteredDatacenters" :key="datacenter.id" class="monitor-panel p-4">
        <div class="flex items-start justify-between gap-3">
          <div class="flex min-w-0 items-center gap-3">
            <div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-cyan-50 text-cyan-700 dark:bg-cyan-950/50 dark:text-cyan-300">
              <UIcon name="i-heroicons-building-office-2" class="h-5 w-5" />
            </div>
            <div class="min-w-0">
              <p class="truncate font-semibold">{{ datacenter.name }}</p>
              <p class="mt-0.5 truncate text-xs text-slate-500 dark:text-slate-400">{{ datacenter.location }} · #{{ datacenter.id }}</p>
            </div>
          </div>
          <div class="flex gap-1">
            <UButton icon="i-heroicons-pencil-square" color="gray" variant="ghost" size="sm" class="h-10 w-10" :aria-label="`Edit ${datacenter.name}`" @click="openEdit(datacenter)" />
            <UButton icon="i-heroicons-trash" color="red" variant="ghost" size="sm" class="h-10 w-10" :aria-label="`Delete ${datacenter.name}`" @click="openDelete(datacenter)" />
          </div>
        </div>
        <p class="mt-4 text-xs text-slate-500 dark:text-slate-400">Created {{ formatDate(datacenter.created_at) }}</p>
      </li>
    </ul>

    <UModal v-model="modalOpen" :prevent-close="saving" :aria-label="editing ? 'Edit Datacenter' : 'Add Datacenter'">
      <UCard class="max-w-lg" :ui="{ background: 'bg-white dark:bg-[#101827]' }">
        <template #header>
          <div>
            <h2 class="text-base font-semibold">{{ editing ? 'Edit Datacenter' : 'Add Datacenter' }}</h2>
            <p class="mt-1 text-sm text-slate-500 dark:text-slate-400">Keep facility identity and location clear for operational scope.</p>
          </div>
        </template>
        <form class="monitor-form space-y-4" @submit.prevent="save">
          <UAlert v-if="formError" color="red" variant="subtle" :title="formError" />
          <UFormGroup label="Name" name="datacenter-name" required>
            <UInput v-model="form.name" required maxlength="255" placeholder="e.g. Amsterdam DC" />
          </UFormGroup>
          <UFormGroup label="Location" name="datacenter-location" required>
            <UInput v-model="form.location" required maxlength="255" placeholder="e.g. Amsterdam, Netherlands" />
          </UFormGroup>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="ghost" :disabled="saving" @click="modalOpen = false">Cancel</UButton>
            <UButton type="submit" :loading="saving">{{ editing ? 'Save changes' : 'Add Datacenter' }}</UButton>
          </div>
        </form>
      </UCard>
    </UModal>

    <ConfirmDialog
      :open="deleteOpen"
      title="Delete Datacenter"
      :description="deleteTarget ? `Delete “${deleteTarget.name}”? Devices must be removed before this facility can be deleted.` : 'Delete this Datacenter?'"
      :require-text="deleteTarget?.name"
      confirm-label="Delete Datacenter"
      :loading="deleteSaving"
      danger
      @update:open="deleteOpen = $event"
      @confirm="confirmDelete"
    />
  </div>
</template>
