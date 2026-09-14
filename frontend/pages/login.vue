<script setup lang="ts">
const auth = useAuth()
const toast = useToast()

const state = reactive({ username: '', password: '' })
const pending = ref(false)
const error = ref<string | null>(null)

async function onSubmit() {
  pending.value = true
  error.value = null
  try {
    await auth.login(state.username, state.password)
    await navigateTo('/')
  } catch (err) {
    // ADR-0003: the backend intentionally returns a uniform 401.
    error.value = errorDetail(err, 'Invalid username or password')
  } finally {
    pending.value = false
  }
}
</script>

<template>
  <div class="min-h-screen flex items-center justify-center">
    <UCard class="w-full max-w-sm">
      <template #header>
        <h1 class="text-lg font-semibold">Sign in to Unplugd</h1>
      </template>
      <UForm :state="state" class="space-y-4" @submit="onSubmit">
        <UFormGroup label="Username" name="username" required>
          <UInput v-model="state.username" autocomplete="username" required />
        </UFormGroup>
        <UFormGroup label="Password" name="password" required>
          <UInput
            v-model="state.password"
            type="password"
            autocomplete="current-password"
            required
          />
        </UFormGroup>
        <UAlert v-if="error" color="red" variant="subtle" :title="error" />
        <UButton type="submit" block :loading="pending">Sign in</UButton>
      </UForm>
    </UCard>
  </div>
</template>
