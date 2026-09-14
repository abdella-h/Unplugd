import type { User, Role } from '~/types/api'

interface JwtClaims {
  sub: string
  role: Role
  dc_id: number | null
  exp: number
}

function decodeClaims(token: string): JwtClaims | null {
  try {
    const payload = token.split('.')[1]
    // JWTs are base64url-encoded: translate to standard base64 and pad.
    const base64 = payload.replace(/-/g, '+').replace(/_/g, '/')
    const padded = base64.padEnd(
      base64.length + ((4 - (base64.length % 4)) % 4),
      '=',
    )
    return JSON.parse(atob(padded)) as JwtClaims
  } catch {
    return null
  }
}

/**
 * Auth state: the access token lives in memory only (never localStorage).
 * On full page load, `init()` exchanges the HttpOnly refresh cookie for a
 * fresh access token (ADR-0004).
 */
export const useAuth = () => {
  const accessToken = useState<string | null>('auth:token', () => null)
  const user = useState<User | null>('auth:user', () => null)
  const ready = useState<boolean>('auth:ready', () => false)

  const setToken = (token: string | null) => {
    accessToken.value = token
    const claims = token ? decodeClaims(token) : null
    user.value = claims
      ? { username: claims.sub, role: claims.role, dcId: claims.dc_id }
      : null
  }

  const login = async (username: string, password: string) => {
    const res = await $fetch<{ access_token: string }>('/api/auth/login', {
      method: 'POST',
      body: { username, password },
    })
    setToken(res.access_token)
  }

  /** Silently exchange the refresh cookie for an access token. */
  const refresh = async (): Promise<boolean> => {
    try {
      const res = await $fetch<{ access_token: string }>('/api/auth/refresh', {
        method: 'POST',
      })
      setToken(res.access_token)
      return true
    } catch {
      setToken(null)
      return false
    }
  }

  const logout = async () => {
    try {
      await $fetch('/api/auth/logout', { method: 'POST' })
    } catch {
      // Best-effort: clear local state regardless.
    }
    setToken(null)
    await navigateTo('/login')
  }

  /** Called once per app load by the route middleware. */
  const init = async () => {
    if (!ready.value) {
      await refresh()
      ready.value = true
    }
  }

  const isAdmin = computed(() => user.value?.role === 'admin')
  const isGlobalAdmin = computed(
    () => isAdmin.value && user.value?.dcId == null,
  )

  return {
    accessToken: readonly(accessToken),
    user: readonly(user),
    ready: readonly(ready),
    isAdmin,
    isGlobalAdmin,
    login,
    refresh,
    logout,
    init,
  }
}
