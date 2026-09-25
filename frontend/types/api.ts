// Types mirroring the backend contracts (services/*/app/schemas).

export type Role = 'admin' | 'operator'

export type DeviceState = 'ok' | 'warning' | 'alert'

export interface User {
  username: string
  role: Role
  /** null for a global admin; always set for operators (ADR-0002). */
  dcId: number | null
}

export interface UserProfile {
  first_name: string | null
  last_name: string | null
  username: string
  email: string
  role: Role
  datacenter_id: number | null
  is_active: boolean
  last_login_at: string | null
}

export interface Datacenter {
  id: number
  name: string
  location: string
  created_at: string
  updated_at: string
}

export interface Device {
  id: number
  datacenter_id: number
  name: string
  type: string
  description: string | null
  serial_number: string | null
  state: DeviceState
  created_at: string
  updated_at: string
}

export interface Alert {
  id: number
  device_id: number
  datacenter_id: number
  old_state: DeviceState
  new_state: DeviceState
  reporter: string
  occurred_at: string
  acknowledged_at: string | null
  acknowledged_by: string | null
}

export interface AcknowledgeResponse extends Alert {
  device_reset_ok: boolean
}

export interface DeviceStatusChangedEvent {
  type: 'device_status_changed'
  device_id: number
  datacenter_id: number
  old_state: DeviceState
  new_state: DeviceState
  reporter: string
  occurred_at: string
}

export interface AlertAcknowledgedEvent {
  type: 'alert_acknowledged_and_resolved'
  alert_id: number
  device_id: number
  datacenter_id: number
  acknowledged_by: string
}

export type StreamEvent = DeviceStatusChangedEvent | AlertAcknowledgedEvent
