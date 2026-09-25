import type { Datacenter } from '~/types/api'

let alertCountSequence = 0

export const useWorkspace = () => {
  const auth = useAuth()
  const { apiFetch } = useApi()
  const datacenters = useState<Datacenter[]>('workspace:datacenters', () => [])
  const datacentersLoaded = useState<boolean>('workspace:datacenters-loaded', () => false)
  const openAlertCount = useState<number | null>('workspace:open-alert-count', () => null)
  const generation = useState<number>('workspace:generation', () => 0)
  const loading = useState<boolean>('workspace:loading', () => false)
  const lastUpdatedAt = useState<number | null>('workspace:last-updated-at', () => null)
  const stale = useState<boolean>('workspace:stale', () => false)
  const sidebarCollapsed = useState<boolean>('shell:sidebar-collapsed', () => false)

  const scopeLabel = computed(() => {
    if (auth.isGlobalAdmin.value) return 'All datacenters'
    const dcId = auth.user.value?.dcId
    if (dcId == null) return 'Datacenter unavailable'
    if (!datacentersLoaded.value) return stale.value ? 'Datacenter unavailable' : 'Loading scope…'
    return datacenters.value.find((datacenter) => datacenter.id === dcId)?.name ?? `Datacenter #${dcId}`
  })

  const roleLabel = computed(() => {
    if (auth.isGlobalAdmin.value) return 'Global Admin'
    if (auth.isAdmin.value) return 'Scoped Admin'
    return 'Operator'
  })

  function datacenterName(id: number): string {
    return datacenters.value.find((datacenter) => datacenter.id === id)?.name ?? `Datacenter #${id}`
  }

  function markFresh(force = false) {
    if (!force && stale.value) return
    lastUpdatedAt.value = Date.now()
    if (auth.isAdmin.value && openAlertCount.value == null) {
      stale.value = true
      return
    }
    stale.value = false
  }

  function markStale() {
    stale.value = true
  }

  async function loadDatacenters(): Promise<boolean> {
    const requestGeneration = generation.value
    try {
      const loadedDatacenters = await apiFetch<Datacenter[]>('/api/devices/datacenters')
      if (requestGeneration !== generation.value) return false
      datacenters.value = loadedDatacenters
      datacentersLoaded.value = true
      return true
    } catch {
      if (requestGeneration === generation.value) markStale()
      return false
    }
  }

  async function refreshAlertCount(): Promise<boolean> {
    const requestGeneration = generation.value
    const requestId = ++alertCountSequence
    if (!auth.isAdmin.value) {
      if (requestGeneration === generation.value && requestId === alertCountSequence) openAlertCount.value = null
      return true
    }
    try {
      const alerts = await apiFetch<unknown[]>('/api/dashboard/alerts?acknowledged=false')
      if (requestGeneration !== generation.value || requestId !== alertCountSequence) return false
      openAlertCount.value = alerts.length
      return true
    } catch {
      if (requestGeneration === generation.value) markStale()
      return false
    }
  }

  function reset() {
    generation.value += 1
    alertCountSequence += 1
    datacenters.value = []
    datacentersLoaded.value = false
    openAlertCount.value = null
    lastUpdatedAt.value = null
    stale.value = false
    loading.value = false
  }

  async function refresh(): Promise<boolean> {
    if (!auth.user.value || loading.value) return false
    const requestGeneration = generation.value
    loading.value = true
    try {
      const datacentersLoadedSuccessfully = await loadDatacenters()
      if (!datacentersLoadedSuccessfully || requestGeneration !== generation.value) return false
      const alertsLoaded = await refreshAlertCount()
      if (requestGeneration !== generation.value) return false
      if (!alertsLoaded) {
        markStale()
        return false
      }
      markFresh(true)
      return true
    } finally {
      if (requestGeneration === generation.value) loading.value = false
    }
  }

  return {
    datacenters,
    datacentersLoaded,
    generation,
    openAlertCount,
    loading,
    lastUpdatedAt,
    stale,
    sidebarCollapsed,
    scopeLabel,
    roleLabel,
    datacenterName,
    reset,
    loadDatacenters,
    refresh,
    refreshAlertCount,
    markFresh,
    markStale,
  }
}
