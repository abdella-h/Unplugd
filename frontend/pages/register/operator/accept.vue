<script setup lang="ts">
definePageMeta({ layout: 'auth' })

const route = useRoute()
const toast = useToast()
const token = computed(() => String(route.query.token ?? ''))
const pending = ref(false)
const error = ref<string | null>(null)
const state = reactive({ username: '', password: '', first_name: '', last_name: '' })

async function onSubmit() {
  if (pending.value || !token.value) return
  pending.value = true
  error.value = null
  try {
    await $fetch('/api/auth/register/operator/accept', {
      method: 'POST',
      body: {
        token: token.value,
        username: state.username,
        password: state.password,
        first_name: state.first_name || null,
        last_name: state.last_name || null,
      },
    })
    toast.add({ title: 'Operator account activated', color: 'green' })
    await navigateTo('/login')
  } catch (caught) {
    error.value = errorDetail(caught, 'Invite is invalid, expired, or already used')
  } finally {
    pending.value = false
  }
}
</script>

<template>
  <UCard class="monitor-panel" :ui="{ background: 'bg-white dark:bg-[#101827]' }">
    <template #header>
      <div>
        <p class="text-xs font-semibold uppercase tracking-[0.16em] text-primary-700 dark:text-primary-300">Operator access</p>
        <h1 class="mt-2 text-2xl font-semibold tracking-tight">Activate your account</h1>
        <p class="mt-2 text-sm text-slate-500 dark:text-slate-400">Choose credentials for the Operator account connected to your invite.</p>
      </div>
    </template>
    <UAlert v-if="!token" color="red" variant="subtle" title="Missing invite token" description="Open the invite link you were sent." />
    <form v-else class="monitor-form space-y-4" @submit.prevent="onSubmit">
      <UFormGroup label="Username" name="username" required>
        <UInput v-model="state.username" autocomplete="username" required minlength="3" />
      </UFormGroup>
      <UFormGroup label="Password" name="password" required>
        <UInput v-model="state.password" type="password" autocomplete="new-password" required minlength="8" />
      </UFormGroup>
      <div class="grid gap-4 sm:grid-cols-2">
        <UFormGroup label="First name" name="first_name">
          <UInput v-model="state.first_name" autocomplete="given-name" />
        </UFormGroup>
        <UFormGroup label="Last name" name="last_name">
          <UInput v-model="state.last_name" autocomplete="family-name" />
        </UFormGroup>
      </div>
      <UAlert v-if="error" color="red" variant="subtle" :title="error" />
      <UButton type="submit" block size="lg" :loading="pending">Activate Operator account</UButton>
    </form>
  </UCard>
</template>
