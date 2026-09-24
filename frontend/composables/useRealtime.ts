import type { StreamEvent } from '~/types/api'

export type RealtimeStatus = 'idle' | 'connecting' | 'connected' | 'reconnecting' | 'offline'

export const useRealtime = () => {
  const auth = useAuth()
  const workspace = useWorkspace()
  const status = useState<RealtimeStatus>('realtime:status', () => 'idle')
  const lastEvent = useState<StreamEvent | null>('realtime:last-event', () => null)
  const events = useState<StreamEvent[]>('realtime:events', () => [])
  const lastTransportAt = useState<number | null>('realtime:last-transport-at', () => null)
  const started = useState<boolean>('realtime:started', () => false)
  const generation = useState<number>('realtime:generation', () => 0)

  let stopped = false
  let abortController: AbortController | null = null

  function consumeEvent(raw: string) {
    try {
      const event = JSON.parse(raw) as StreamEvent
      if (event.type !== 'device_status_changed' && event.type !== 'alert_acknowledged_and_resolved') return
      events.value = [event, ...events.value].slice(0, 50)
      lastEvent.value = event
      const eventGeneration = workspace.generation.value
      void workspace.refreshAlertCount().then((loaded) => {
        if (!loaded && workspace.generation.value === eventGeneration) workspace.markStale()
      })
    } catch {
      return
    }
  }

  function parseFrames(buffer: string): { frames: string[]; remainder: string } {
    const normalized = buffer.replace(/\r\n/g, '\n')
    const frames = normalized.split('\n\n')
    return {
      frames: frames.slice(0, -1),
      remainder: frames.at(-1) ?? '',
    }
  }

  async function connect(): Promise<void> {
    if (started.value || !auth.isAdmin.value) return
    started.value = true
    stopped = false
    const connectionGeneration = generation.value
    const isCurrent = () => generation.value === connectionGeneration

    while (!stopped && isCurrent()) {
      abortController = new AbortController()
      status.value = status.value === 'idle' ? 'connecting' : 'reconnecting'

      try {
        let token = auth.accessToken.value
        if (!token && !(await auth.refresh())) {
          if (isCurrent()) {
            status.value = 'offline'
            started.value = false
          }
          return
        }
        token = auth.accessToken.value

        const response = await fetch('/api/dashboard/stream', {
          headers: {
            Authorization: `Bearer ${token}`,
            Accept: 'text/event-stream',
          },
          signal: abortController.signal,
        })

        if (!isCurrent()) return
        if (response.status === 401 && (await auth.refresh())) continue
        if (!response.ok || !response.body) throw new Error('Stream unavailable')

        status.value = 'connected'
        lastTransportAt.value = Date.now()
        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''

        for (;;) {
          const { done, value } = await reader.read()
          if (!isCurrent()) return
          if (done) break
          lastTransportAt.value = Date.now()
          buffer += decoder.decode(value, { stream: true })
          const parsed = parseFrames(buffer)
          buffer = parsed.remainder
          for (const frame of parsed.frames) {
            for (const line of frame.split('\n')) {
              if (line.startsWith('data:')) consumeEvent(line.slice(5).trim())
            }
          }
        }
      } catch {
        if (!stopped && isCurrent()) {
          status.value = import.meta.client && !navigator.onLine ? 'offline' : 'reconnecting'
        }
      }

      if (!stopped && isCurrent()) {
        await new Promise((resolve) => setTimeout(resolve, 3000))
      }
    }

    if (isCurrent()) {
      status.value = stopped ? 'idle' : 'offline'
      started.value = false
    }
  }

  function clear() {
    disconnect()
    events.value = []
    lastEvent.value = null
    lastTransportAt.value = null
  }

  function disconnect() {
    generation.value += 1
    stopped = true
    abortController?.abort()
    abortController = null
    started.value = false
    status.value = 'idle'
  }

  return {
    status,
    lastEvent,
    events,
    lastTransportAt,
    connect,
    disconnect,
    clear,
  }
}
