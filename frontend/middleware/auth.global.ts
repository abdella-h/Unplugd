const PUBLIC_PREFIXES = ['/login', '/setup', '/register/operator/accept']

export default defineNuxtRouteMiddleware(async (to) => {
  const auth = useAuth()
  await auth.init()

  const isPublic = PUBLIC_PREFIXES.some((p) => to.path.startsWith(p))

  if (!auth.user.value) {
    return isPublic ? undefined : navigateTo('/login')
  }
  // Logged-in users have no business on the public pages.
  if (isPublic) {
    return navigateTo('/')
  }
})
