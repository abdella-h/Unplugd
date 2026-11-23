const PUBLIC_PREFIXES = ['/login', '/setup', '/register/operator/accept']
const SETUP_EXEMPT_PREFIXES = ['/setup', '/register/operator/accept']

export default defineNuxtRouteMiddleware(async (to) => {
  const auth = useAuth()
  await auth.init()

  const isPublic = PUBLIC_PREFIXES.some((p) => to.path.startsWith(p))

  if (auth.user.value) {
    // Logged-in users have no business on the public pages.
    return isPublic ? navigateTo('/') : undefined
  }

  const setup = useSetup()
  const needsSetup = await setup.ensureStatus()
  const isSetupExempt = SETUP_EXEMPT_PREFIXES.some((p) =>
    to.path.startsWith(p),
  )

  if (needsSetup === true) {
    return isSetupExempt ? undefined : navigateTo('/setup')
  }

  // Setup is complete: /setup is a dead end. A failed status probe fails
  // open to the sign-in page.
  if (to.path.startsWith('/setup')) return navigateTo('/login')

  return isPublic ? undefined : navigateTo('/login')
})
