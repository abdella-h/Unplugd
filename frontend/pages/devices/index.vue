<script setup lang="ts">
import type { Datacenter, Device, DeviceState } from '~/types/api'

const auth = useAuth()
const { apiFetch } = useApi()
const toast = useToast()

const devices = ref<Device[]>([])
const datacenters = ref<Datacenter[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

const stateOptions: DeviceState[] = ['ok', 'warning', 'alert']

async function load() {
  loading.value = true
  error.value = null
  try {
    devices.value = await apiFetch<Device[]>('/api/devices/devices')
    // Datacenters list is global-admin only; scoped admins use their dcId.
    if (auth.isGlobalAdmin.value) {
      datacenters.value = await apiFetch<Datacenter[]>(
        '/api/devices/datacenters',
      )
    }
  } catch (err) {
    error.value = errorDetail(err)
  } finally {
    loading.value = false
  }
}

onMounted(load)

const dcName = (id: number) =>
  datacenters.value.find((d) => d.id === id)?.name ?? `#${id}`

const columns = computed(() => {
  const cols = [
    { key: 'name', label: 'Name' },
    { key: 'datacenter', label: 'Datacenter' },
    { key: 'type', label: 'Type' },
    { key: 'serial_number', label: 'Serial' },
    { key: 'state', label: 'State' },
  ]
  if (auth.isAdmin.value) cols.push({ key: 'actions', label: '' })
  return cols
})

// --- operator / scoped state change ---
async function setState(device: Device, state: DeviceState) {
  try {
    const updated = await apiFetch<Device>(
      `/api/devices/devices/${device.id}/state`,
      { method: 'PUT', body: { state } },
    )
    Object.assign(device, updated)
  } catch (err) {
    toast.add({ title: errorDetail(err), color: 'red' })
  }
}

// --- admin create / edit / delete ---
const isGlobalAdmin = auth.isGlobalAdmin
const modalOpen = ref(false)
const editing = ref<Device | null>(null)
const saving = ref(false)
const form = reactive({
  name: '',
  datacenter_id: undefined as number | undefined,
  type: '',
  description: '',
  serial_number: '',
  state: 'ok' as DeviceState,
})

function openCreate() {
  editing.value = null
  Object.assign(form, {
    name: '',
    datacenter_id: auth.user.value?.dcId ?? datacenters.value[0]?.id,
    type: '',
    description: '',
    serial_number: '',
    state: 'ok',
  })
  modalOpen.value = true
}

function openEdit(device: Device) {
  editing.value = device
  Object.assign(form, {
    name: device.name,
    datacenter_id: device.datacenter_id,
    type: device.type,
    description: device.description ?? '',
    serial_number: device.serial_number ?? '',
    state: device.state,
  })
  modalOpen.value = true
}

async function save() {
  saving.value = true
  try {
    if (editing.value) {
      // datacenter_id is immutable via PATCH and state is reported via the
      // dedicated state sub-resource; only send editable inventory fields.
      const updated = await apiFetch<Device>(
        `/api/devices/devices/${editing.value.id}`,
        {
          method: 'PATCH',
          body: {
            name: form.name,
            type: form.type,
            description: form.description || null,
            serial_number: form.serial_number || null,
          },
        },
      )
      Object.assign(editing.value, updated)
    } else {
      const created = await apiFetch<Device>('/api/devices/devices', {
        method: 'POST',
        body: {
          name: form.name,
          datacenter_id: form.datacenter_id,
          type: form.type,
          description: form.description || undefined,
          serial_number: form.serial_number || undefined,
          state: form.state,
        },
      })
      devices.value.push(created)
    }
    modalOpen.value = false
  } catch (err) {
    toast.add({ title: errorDetail(err), color: 'red' })
  } finally {
    saving.value = false
  }
}

// --- operator invite (admin) ---
const inviteOpen = ref(false)
const inviteSaving = ref(false)
const invite = reactive({ email: '', datacenter_id: undefined as number | undefined })
const inviteLink = ref<string | null>(null)

function openInvite() {
  Object.assign(invite, {
    email: '',
    datacenter_id: auth.user.value?.dcId ?? datacenters.value[0]?.id,
  })
  inviteLink.value = null
  inviteOpen.value = true
}

async function sendInvite() {
  inviteSaving.value = true
  try {
    const res = await apiFetch<{ invite_link: string }>(
      '/api/auth/register/operator/invite',
      { method: 'POST', body: { email: invite.email, datacenter_id: invite.datacenter_id } },
    )
    inviteLink.value = res.invite_link
  } catch (err) {
    toast.add({ title: errorDetail(err), color: 'red' })
  } finally {
    inviteSaving.value = false
  }
}

async function remove(device: Device) {
  if (!window.confirm(`Delete device "${device.name}"?`)) return
  try {
    await apiFetch(`/api/devices/devices/${device.id}`, { method: 'DELETE' })
    devices.value = devices.value.filter((d) => d.id !== device.id)
  } catch (err) {
    toast.add({ title: errorDetail(err), color: 'red' })
  }
}
</script>

<template>
  <div>
    <AppHeader />
    <main class="p-4 space-y-4">
      <div class="flex items-center justify-between">
        <h1 class="text-xl font-semibold">Devices</h1>
        <div v-if="auth.isAdmin.value" class="flex gap-2">
          <UButton icon="i-heroicons-envelope" color="gray" @click="openInvite">
            Invite operator
          </UButton>
          <UButton icon="i-heroicons-plus" @click="openCreate">
            Add device
          </UButton>
        </div>
      </div>

      <UAlert v-if="error" color="red" variant="subtle" :title="error" />
      <UTable :rows="devices" :columns="columns" :loading="loading">
        <template #datacenter-data="{ row }">
          {{ dcName(row.datacenter_id) }}
        </template>
        <template #serial_number-data="{ row }">
          {{ row.serial_number ?? '—' }}
        </template>
        <template #state-data="{ row }">
          <div class="flex items-center gap-2">
            <StateBadge :state="row.state" />
            <USelectMenu
              :model-value="row.state"
              :options="stateOptions"
              size="xs"
              class="w-28"
              @update:model-value="(s: DeviceState) => setState(row, s)"
            />
          </div>
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

      <UModal v-model="inviteOpen">
        <UCard>
          <template #header>
            <h2 class="font-semibold">Invite operator</h2>
          </template>
          <div v-if="inviteLink" class="space-y-3">
            <UAlert
              color="green"
              variant="subtle"
              title="Invite created. Send this link to the operator:"
            />
            <code class="block break-all text-sm">{{ inviteLink }}</code>
            <div class="flex justify-end">
              <UButton color="gray" @click="inviteOpen = false">Close</UButton>
            </div>
          </div>
          <UForm v-else :state="invite" class="space-y-4" @submit="sendInvite">
            <UFormGroup label="Email" name="email" required>
              <UInput v-model="invite.email" type="email" required />
            </UFormGroup>
            <UFormGroup label="Datacenter" name="datacenter" required>
              <USelect
                v-model="invite.datacenter_id"
                :options="datacenters"
                option-attribute="name"
                value-attribute="id"
                required
                :disabled="auth.user.value?.dcId != null"
              />
            </UFormGroup>
            <div class="flex justify-end gap-2">
              <UButton color="gray" variant="ghost" @click="inviteOpen = false">
                Cancel
              </UButton>
              <UButton type="submit" :loading="inviteSaving">Send invite</UButton>
            </div>
          </UForm>
        </UCard>
      </UModal>

      <UModal v-model="modalOpen">
        <UCard>
          <template #header>
            <h2 class="font-semibold">
              {{ editing ? 'Edit device' : 'Add device' }}
            </h2>
          </template>
          <UForm :state="form" class="space-y-4" @submit="save">
            <UFormGroup label="Name" name="name" required>
              <UInput v-model="form.name" required />
            </UFormGroup>
            <UFormGroup v-if="!editing && isGlobalAdmin" label="Datacenter" required>
              <USelect
                v-model="form.datacenter_id"
                :options="datacenters"
                option-attribute="name"
                value-attribute="id"
                required
              />
            </UFormGroup>
            <UFormGroup label="Type" name="type" required>
              <UInput v-model="form.type" required />
            </UFormGroup>
            <UFormGroup label="Description" name="description">
              <UInput v-model="form.description" />
            </UFormGroup>
            <UFormGroup label="Serial number" name="serial_number">
              <UInput v-model="form.serial_number" />
            </UFormGroup>
            <UFormGroup v-if="!editing" label="Initial state" name="state">
              <USelect v-model="form.state" :options="stateOptions" />
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
