<script setup lang="ts">
const toast = useToast()

const needsSetup = ref<boolean | null>(null)
const pending = ref(false)
const error = ref<string | null>(null)

const state = reactive({
  first_name: '',
  last_name: '',
  username: '',
  email: '',
  password: '',
})

onMounted(async () => {
  try {
    const res = await $fetch<{ needs_setup: boolean }>('/api/auth/setup/status')
    needsSetup.value = res.needs_setup
  } catch {
    error.value = 'Could not reach the auth service'
  }
})

async function onSubmit() {
  pending.value = true
  error.value = null
  try {
    await $fetch('/api/auth/setup', {
      method: 'POST',
      body: {
        // InitialAdminCreate requires first_name/last_name keys (nullable,
        // no default): send null rather than omitting them.
        first_name: state.first_name || null,
        last_name: state.last_name || null,
        username: state.username,
        email: state.email,
        password: state.password,
      },
    })
    toast.add({ title: 'Admin account created', color: 'green' })
    await navigateTo('/login')
  } catch (err) {
    error.value = errorDetail(err)
  } finally {
    pending.value = false
  }
}
</script>

<template>
  <div class="min-h-screen flex items-center justify-center">
    <UCard class="w-full max-w-md">
      <template #header>
        <h1 class="text-lg font-semibold">First-run setup</h1>
      </template>
      <UAlert
        v-if="needsSetup === false"
        color="blue"
        variant="subtle"
        title="Setup already completed"
        description="An admin account already exists."
      >
        <template #actions>
          <UButton to="/login" size="xs">Go to sign in</UButton>
        </template>
      </UAlert>
      <template v-else-if="needsSetup">
        <p class="text-sm text-gray-500 mb-4">
          Create the first global admin account.
        </p>
        <UForm :state="state" class="space-y-4" @submit="onSubmit">
          <div class="grid grid-cols-2 gap-4">
            <UFormGroup label="First name" name="first_name">
              <UInput v-model="state.first_name" />
            </UFormGroup>
            <UFormGroup label="Last name" name="last_name">
              <UInput v-model="state.last_name" />
            </UFormGroup>
          </div>
          <UFormGroup label="Username" name="username" required>
            <UInput v-model="state.username" required />
          </UFormGroup>
          <UFormGroup label="Email" name="email" required>
            <UInput v-model="state.email" type="email" required />
          </UFormGroup>
          <UFormGroup label="Password" name="password" required>
            <UInput v-model="state.password" type="password" required />
          </UFormGroup>
          <UAlert v-if="error" color="red" variant="subtle" :title="error" />
          <UButton type="submit" block :loading="pending">
            Create admin account
          </UButton>
        </UForm>
      </template>
    </UCard>
  </div>
</template>
