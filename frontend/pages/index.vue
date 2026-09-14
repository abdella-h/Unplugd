<script setup lang="ts">
// Landing: admins go to the alert dashboard, operators to their devices.
const auth = useAuth()
if (auth.isAdmin.value) {
  await navigateTo('/alerts')
} else {
  await navigateTo('/devices')
}
</script>

<template>
  <div />
</template>
