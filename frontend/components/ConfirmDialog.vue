<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    open: boolean
    title: string
    description: string
    confirmLabel?: string
    requireText?: string
    loading?: boolean
    danger?: boolean
  }>(),
  {
    confirmLabel: 'Confirm',
    loading: false,
    danger: false,
  },
)

const emit = defineEmits<{
  'update:open': [value: boolean]
  confirm: []
}>()

const confirmation = ref('')
const canConfirm = computed(
  () => !props.loading && (!props.requireText || confirmation.value.trim() === props.requireText),
)

watch(
  () => props.open,
  (open) => {
    if (open) confirmation.value = ''
  },
)
</script>

<template>
  <UModal
    :model-value="open"
    :prevent-close="loading"
    :aria-label="title"
    @update:model-value="emit('update:open', $event)"
  >
    <UCard class="max-w-md" :ui="{ background: 'bg-white dark:bg-[#101827]' }">
      <template #header>
        <div class="flex items-start gap-3">
          <div
            class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg"
            :class="danger ? 'bg-red-50 text-red-600 dark:bg-red-950/50 dark:text-red-300' : 'bg-cyan-50 text-cyan-700 dark:bg-cyan-950/50 dark:text-cyan-300'"
          >
            <UIcon :name="danger ? 'i-heroicons-exclamation-triangle' : 'i-heroicons-question-mark-circle'" class="h-5 w-5" />
          </div>
          <div>
            <h2 class="text-base font-semibold">{{ title }}</h2>
            <p class="mt-1 text-sm text-slate-500 dark:text-slate-400">{{ description }}</p>
          </div>
        </div>
      </template>
      <div v-if="requireText" class="space-y-2">
        <UFormGroup :label="`Type ${requireText} to continue`" :name="requireText">
          <UInput v-model="confirmation" autocomplete="off" />
        </UFormGroup>
      </div>
      <template #footer>
        <div class="flex justify-end gap-2">
          <UButton color="gray" variant="ghost" :disabled="loading" @click="emit('update:open', false)">
            Cancel
          </UButton>
          <UButton
            :color="danger ? 'red' : 'primary'"
            :loading="loading"
            :disabled="!canConfirm"
            @click="emit('confirm')"
          >
            {{ confirmLabel }}
          </UButton>
        </div>
      </template>
    </UCard>
  </UModal>
</template>
