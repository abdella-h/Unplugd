import type { NitroFetchOptions, NitroFetchRequest } from 'nitropack'

/**
 * Authenticated fetch wrapper. Attaches the in-memory access token; on a
 * 401 it attempts one silent refresh (ADR-0004 rotation) and retries once.
 */
export const useApi = () => {
  const auth = useAuth()

  const sessionKey = () => {
    const user = auth.user.value
    return user ? `${user.username}|${user.role}|${user.dcId ?? ''}` : ''
  }

  const apiFetch = async <T>(
    path: string,
    opts: NitroFetchOptions<NitroFetchRequest> = {},
  ): Promise<T> => {
    const withAuth = () =>
      $fetch<T>(path, {
        ...opts,
        headers: {
          ...(opts.headers as Record<string, string> | undefined),
          ...(auth.accessToken.value
            ? { Authorization: `Bearer ${auth.accessToken.value}` }
            : {}),
        },
      })

    const requestSession = sessionKey()
    const requestEpoch = auth.sessionEpoch.value
    const sessionIsCurrent = () =>
      sessionKey() === requestSession && auth.sessionEpoch.value === requestEpoch
    try {
      const result = await withAuth()
      if (!sessionIsCurrent()) throw new Error('Session changed')
      return result
    } catch (err: any) {
      if (!sessionIsCurrent()) throw err
      if (err?.response?.status === 401 && (await auth.refresh())) {
        const result = await withAuth()
        if (!sessionIsCurrent()) throw new Error('Session changed')
        return result
      }
      throw err
    }
  }

  return { apiFetch }
}

/** Best-effort extraction of a FastAPI error detail for display. */
export function errorDetail(err: unknown, fallback = 'Request failed'): string {
  const detail = (err as any)?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg as string
  return fallback
}
