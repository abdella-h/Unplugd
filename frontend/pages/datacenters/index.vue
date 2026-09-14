<script setup lang="ts">
import type { Datacenter } from '~/types/api'

const auth = useAuth()
const { apiFetch } = useApi()
const toast = useToast()

// Global admins only (devices service 403s otherwise).
if (!auth.isGlobalAdmin.value) {
  await navigateTo('/')
}

const datacenters = ref<Datacenter[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

async function load() {
  loading.value = true
  error.value = null
  try {
    datacenters.value = await apiFetch<Datacenter[]>('/api/devices/datacenters')
  } catch (err) {
    error.value = errorDetail(err)
  } finally {
    loading.value = false
  }
}

onMounted(load)

const columns = [
  { key: 'name', label: 'Name' },
  { key: 'location', label: 'Location' },
  { key: 'created_at', label: 'Created' },
  { key: 'actions', label: '' },
]

const modalOpen = ref(false)
const editing = ref<Datacenter | null>(null)
const saving = ref(false)
const form = reactive({ name: '', location: '' })

function openCreate() {
  editing.value = null
  Object.assign(form, { name: '', location: '' })
  modalOpen.value = true
}

function openEdit(dc: Datacenter) {
  editing.value = dc
  Object.assign(form, { name: dc.name, location: dc.location })
  modalOpen.value = true
}

async function save() {
  saving.value = true
  try {
    if (editing.value) {
      const updated = await apiFetch<Datacenter>(
        `/api/devices/datacenters/${editing.value.id}`,
        { method: 'PATCH', body: { ...form } },
      )
      Object.assign(editing.value, updated)
    } else {
      const created = await apiFetch<Datacenter>('/api/devices/datacenters', {
        method: 'POST',
        body: { ...form },
      })
      datacenters.value.push(created)
    }
    modalOpen.value = false
  } catch (err) {
    toast.add({ title: errorDetail(err), color: 'red' })
  } finally {
    saving.value = false
  }
}

async function remove(dc: Datacenter) {
  if (!window.confirm(`Delete datacenter "${dc.name}"?`)) return
  try {
    await apiFetch(`/api/devices/datacenters/${dc.id}`, { method: 'DELETE' })
    datacenters.value = datacenters.value.filter((d) => d.id !== dc.id)
  } catch (err) {
    // 409 when devices still exist in the datacenter.
    toast.add({ title: errorDetail(err), color: 'red' })
  }
}
</script>

<template>
  <div>
    <AppHeader />
    <main class="p-4 space-y-4">
      <div class="flex items-center justify-between">
        <h1 class="text-xl font-semibold">Datacenters</h1>
        <UButton icon="i-heroicons-plus" @click="openCreate">
          Add datacenter
        </UButton>
      </div>

      <UAlert v-if="error" color="red" variant="subtle" :title="error" />
      <UTable :rows="datacenters" :columns="columns" :loading="loading">
        <template #created_at-data="{ row }">
          {{ new Date(row.created_at).toLocaleString() }}
        </template>
        <template #actions-data="{ row }">
          <div class="flex gap-1 justify-end">
            <UButton
              icon="i-heroicons-pencil-square"
              size="xs"
              color="gray"
              variant="ghost"
              @click="openEdit(row)"
            />
            <UButton
              icon="i-heroicons-trash"
              size="xs"
              color="red"
              variant="ghost"
              @click="remove(row)"
            />
          </div>
        </template>
      </UTable>

      <UModal v-model="modalOpen">
        <UCard>
          <template #header>
            <h2 class="font-semibold">
              {{ editing ? 'Edit datacenter' : 'Add datacenter' }}
            </h2>
          </template>
          <UForm :state="form" class="space-y-4" @submit="save">
            <UFormGroup label="Name" name="name" required>
              <UInput v-model="form.name" required />
            </UFormGroup>
            <UFormGroup label="Location" name="location" required>
              <UInput v-model="form.location" required />
            </UFormGroup>
            <div class="flex justify-end gap-2">
              <UButton color="gray" variant="ghost" @click="modalOpen = false">
                Cancel
              </UButton>
              <UButton type="submit" :loading="saving">Save</UButton>
            </div>
          </UForm>
        </UCard>
      </UModal>
    </main>
  </div>
</template>
