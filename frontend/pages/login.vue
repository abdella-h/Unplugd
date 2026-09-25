<script setup lang="ts">
definePageMeta({ layout: 'auth' })

const auth = useAuth()
const state = reactive({ username: '', password: '' })
const pending = ref(false)
const error = ref<string | null>(null)

async function onSubmit() {
  if (pending.value) return
  pending.value = true
  error.value = null
  try {
    await auth.login(state.username, state.password)
    await navigateTo('/')
  } catch (caught) {
    error.value = errorDetail(caught, 'Invalid username or password')
  } finally {
    pending.value = false
  }
}
</script>

<template>
  <UCard class="monitor-panel" :ui="{ background: 'bg-white dark:bg-[#101827]' }">
    <template #header>
      <div>
        <p class="text-xs font-semibold uppercase tracking-[0.16em] text-primary-700 dark:text-primary-300">Secure access</p>
        <h1 class="mt-2 text-2xl font-semibold tracking-tight">Sign in to Unplugd</h1>
        <p class="mt-2 text-sm text-slate-500 dark:text-slate-400">Use your assigned account to access operational context.</p>
      </div>
    </template>
    <form class="monitor-form space-y-5" @submit.prevent="onSubmit">
      <UFormGroup label="Username" name="username" required>
        <UInput v-model="state.username" autocomplete="username" required autofocus />
      </UFormGroup>
      <UFormGroup label="Password" name="password" required>
        <UInput v-model="state.password" type="password" autocomplete="current-password" required />
      </UFormGroup>
      <UAlert v-if="error" color="red" variant="subtle" :title="error" />
      <UButton type="submit" block size="lg" :loading="pending">Sign in</UButton>
    </form>
    <p class="mt-5 text-center text-xs text-slate-500 dark:text-slate-400">Access is scoped to your role and assigned Datacenter.</p>
  </UCard>
</template>
