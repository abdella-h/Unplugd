<script setup lang="ts">
definePageMeta({ layout: 'auth' })

const toast = useToast()
const needsSetup = ref<boolean | null>(null)
const checkingSetup = ref(true)
const pending = ref(false)
const error = ref<string | null>(null)
const state = reactive({ first_name: '', last_name: '', username: '', email: '', password: '' })

async function checkStatus() {
  checkingSetup.value = true
  error.value = null
  try {
    const response = await $fetch<{ needs_setup: boolean }>('/api/auth/setup/status')
    needsSetup.value = response.needs_setup
  } catch (caught) {
    error.value = errorDetail(caught, 'Could not reach the auth service')
  } finally {
    checkingSetup.value = false
  }
}

async function onSubmit() {
  if (pending.value) return
  pending.value = true
  error.value = null
  try {
    await $fetch('/api/auth/setup', {
      method: 'POST',
      body: {
        first_name: state.first_name || null,
        last_name: state.last_name || null,
        username: state.username,
        email: state.email,
        password: state.password,
      },
    })
    toast.add({ title: 'Admin account created', color: 'green' })
    await navigateTo('/login')
  } catch (caught) {
    error.value = errorDetail(caught)
  } finally {
    pending.value = false
  }
}

onMounted(checkStatus)
</script>

<template>
  <UCard class="monitor-panel" :ui="{ background: 'bg-white dark:bg-[#101827]' }">
    <template #header>
      <div>
        <p class="text-xs font-semibold uppercase tracking-[0.16em] text-primary-700 dark:text-primary-300">First run</p>
        <h1 class="mt-2 text-2xl font-semibold tracking-tight">Set up your workspace</h1>
        <p class="mt-2 text-sm text-slate-500 dark:text-slate-400">Create the first Global Admin account for this Unplugd deployment.</p>
      </div>
    </template>

    <div v-if="checkingSetup" class="space-y-4" aria-label="Checking setup status" role="status" aria-busy="true">
      <span class="sr-only">Checking setup status</span>
      <div class="monitor-skeleton h-5 w-2/5 rounded" />
      <div class="monitor-skeleton h-10 w-full rounded-md" />
      <div class="monitor-skeleton h-10 w-full rounded-md" />
    </div>
    <UAlert v-else-if="error && needsSetup === null" color="red" variant="subtle" title="Setup status unavailable" :description="error">
      <template #actions>
        <UButton size="xs" color="red" variant="soft" @click="checkStatus">Retry</UButton>
      </template>
    </UAlert>
    <UAlert v-else-if="needsSetup === false" color="blue" variant="subtle" title="Setup already completed" description="An admin account already exists.">
      <template #actions>
        <UButton to="/login" size="xs">Go to sign in</UButton>
      </template>
    </UAlert>
    <form v-else-if="needsSetup" class="monitor-form space-y-4" @submit.prevent="onSubmit">
      <div class="grid gap-4 sm:grid-cols-2">
        <UFormGroup label="First name" name="first_name">
          <UInput v-model="state.first_name" autocomplete="given-name" />
        </UFormGroup>
        <UFormGroup label="Last name" name="last_name">
          <UInput v-model="state.last_name" autocomplete="family-name" />
        </UFormGroup>
      </div>
      <UFormGroup label="Username" name="username" required>
        <UInput v-model="state.username" autocomplete="username" required />
      </UFormGroup>
      <UFormGroup label="Email" name="email" required>
        <UInput v-model="state.email" type="email" autocomplete="email" required />
      </UFormGroup>
      <UFormGroup label="Password" name="password" required>
        <UInput v-model="state.password" type="password" autocomplete="new-password" required minlength="8" />
      </UFormGroup>
      <UAlert v-if="error" color="red" variant="subtle" :title="error" />
      <UButton type="submit" block size="lg" :loading="pending">Create Global Admin account</UButton>
    </form>
  </UCard>
</template>
