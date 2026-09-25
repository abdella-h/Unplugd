import type { UserProfile } from '~/types/api'
import { errorDetail } from '~/composables/useApi'

let requestSequence = 0

export const useUserProfile = () => {
  const auth = useAuth()
  const { apiFetch } = useApi()
  const profile = useState<UserProfile | null>('auth:profile', () => null)
  const loading = useState<boolean>('auth:profile-loading', () => false)
  const error = useState<string | null>('auth:profile-error', () => null)

  const displayName = computed(() => {
    const fullName = [profile.value?.first_name, profile.value?.last_name]
      .map((name) => name?.trim() ?? '')
      .filter(Boolean)
      .join(' ')
    return fullName || profile.value?.username || auth.user.value?.username || ''
  })

  const initials = computed(() => {
    const parts = displayName.value.split(/\s+/).filter(Boolean)
    if (parts.length === 0) return 'U'
    if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
    return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase()
  })

  const datacenterId = computed(
    () => profile.value?.datacenter_id ?? auth.user.value?.dcId,
  )

  const isGlobalAdmin = computed(() => {
    const role = profile.value?.role ?? auth.user.value?.role
    return role === 'admin' && datacenterId.value == null
  })

  const roleLabel = computed(() => {
    const role = profile.value?.role ?? auth.user.value?.role
    if (role === 'admin') return isGlobalAdmin.value ? 'Global Admin' : 'Scoped Admin'
    return 'Operator'
  })

  const reset = () => {
    requestSequence += 1
    profile.value = null
    loading.value = false
    error.value = null
  }

  const load = async (force = false): Promise<boolean> => {
    if (!auth.user.value || loading.value) return Boolean(profile.value)
    if (profile.value && !force) return true

    const sequence = ++requestSequence
    const requestEpoch = auth.sessionEpoch.value
    loading.value = true
    error.value = null
    try {
      const loaded = await apiFetch<UserProfile>('/api/auth/me')
      if (
        sequence !== requestSequence ||
        requestEpoch !== auth.sessionEpoch.value ||
        !auth.user.value
      ) {
        return false
      }
      profile.value = loaded
      return true
    } catch (caught) {
      if (sequence === requestSequence && requestEpoch === auth.sessionEpoch.value) {
        error.value = errorDetail(caught, 'Profile could not be loaded')
      }
      return false
    } finally {
      if (sequence === requestSequence) loading.value = false
    }
  }

  return {
    profile,
    loading,
    error,
    displayName,
    initials,
    datacenterId,
    isGlobalAdmin,
    roleLabel,
    load,
    reset,
  }
}
