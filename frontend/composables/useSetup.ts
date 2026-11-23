/**
 * First-run setup status. The result is cached per app load so the global
 * middleware does not probe the auth service on every unauthenticated
 * navigation. Failures are not cached, so the next navigation retries.
 */
export const useSetup = () => {
  const needsSetup = useState<boolean | null>('setup:needs-setup', () => null)

  async function checkStatus(): Promise<boolean> {
    const response = await $fetch<{ needs_setup: boolean }>(
      '/api/auth/setup/status',
    )
    needsSetup.value = response.needs_setup
    return response.needs_setup
  }

  async function ensureStatus(): Promise<boolean | null> {
    if (needsSetup.value !== null) return needsSetup.value
    try {
      return await checkStatus()
    } catch {
      return null
    }
  }

  function markSetupComplete() {
    needsSetup.value = false
  }

  return { needsSetup, checkStatus, ensureStatus, markSetupComplete }
}
