<script setup lang="ts">
const route = useRoute()
const toast = useToast()

const token = computed(() => String(route.query.token ?? ''))
const pending = ref(false)
const error = ref<string | null>(null)

const state = reactive({
  username: '',
  password: '',
  first_name: '',
  last_name: '',
})

async function onSubmit() {
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
    toast.add({ title: 'Account activated', color: 'green' })
    await navigateTo('/login')
  } catch (err) {
    error.value = errorDetail(err, 'Invite is invalid, expired, or already used')
  } finally {
    pending.value = false
  }
}
</script>

<template>
  <div class="min-h-screen flex items-center justify-center">
    <UCard class="w-full max-w-md">
      <template #header>
        <h1 class="text-lg font-semibold">Activate operator account</h1>
      </template>
      <UAlert
        v-if="!token"
        color="red"
        variant="subtle"
        title="Missing invite token"
        description="Open the invite link you were sent."
      />
      <UForm v-else :state="state" class="space-y-4" @submit="onSubmit">
        <UFormGroup label="Username" name="username" required>
          <UInput v-model="state.username" required minlength="3" />
        </UFormGroup>
        <UFormGroup label="Password" name="password" required>
          <UInput v-model="state.password" type="password" required minlength="8" />
        </UFormGroup>
        <div class="grid grid-cols-2 gap-4">
          <UFormGroup label="First name" name="first_name">
            <UInput v-model="state.first_name" />
          </UFormGroup>
          <UFormGroup label="Last name" name="last_name">
            <UInput v-model="state.last_name" />
          </UFormGroup>
        </div>
        <UAlert v-if="error" color="red" variant="subtle" :title="error" />
        <UButton type="submit" block :loading="pending">Activate</UButton>
      </UForm>
    </UCard>
  </div>
</template>
