import axios from 'axios'

function getToken() {
  return localStorage.getItem('smwcs_token')
}

function authHeaders() {
  const token = getToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

// Auth
export const authApi = {
  login: (email, password) =>
    axios.post('/auth/api/v1/auth/login', { email, password }),
  me: () =>
    axios.get('/auth/api/v1/auth/me', { headers: authHeaders() }),
}

// Command API
export const commandApi = {
  getFleetLive:     () => axios.get('/command/api/v1/fleet/live',        { headers: authHeaders() }),
  getFleetStats:    () => axios.get('/command/api/v1/fleet/stats',       { headers: authHeaders() }),
  getAlerts:   (p) => axios.get('/command/api/v1/alerts/',               { headers: authHeaders(), params: p }),
  getAlertStats:    () => axios.get('/command/api/v1/alerts/stats',      { headers: authHeaders() }),
  acknowledgeAlert: (id) => axios.post(`/command/api/v1/alerts/${id}/acknowledge`, {}, { headers: authHeaders() }),
  resolveAlert:     (id) => axios.post(`/command/api/v1/alerts/${id}/resolve`,     {}, { headers: authHeaders() }),
  getSummary:       () => axios.get('/command/api/v1/analytics/summary', { headers: authHeaders() }),
}

// Bins
export const binsApi = {
  getBins:  (p) => axios.get('/bins/api/v1/bins/',  { headers: authHeaders(), params: p }),
  getZones: ()  => axios.get('/bins/api/v1/zones/', { headers: authHeaders() }),
}

// Fleet service
export const fleetApi = {
  getTrucks:  () => axios.get('/fleet/api/v1/trucks/',  { headers: authHeaders() }),
  getDrivers: () => axios.get('/fleet/api/v1/drivers/', { headers: authHeaders() }),
  getShifts:  () => axios.get('/fleet/api/v1/shifts/',  { headers: authHeaders() }),
}

// WebSocket — connects directly, no proxy needed
export function createDashboardWS(onMessage, onConnect, onDisconnect) {
  const WS_URL = 'ws://localhost:8007/ws/dashboard'
  let ws = null
  let pingInterval = null

  function connect() {
    ws = new WebSocket(WS_URL)

    ws.onopen = () => {
      onConnect?.()
      pingInterval = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) ws.send('ping')
      }, 30000)
    }

    ws.onmessage = (event) => {
      if (event.data === 'pong') return
      try {
        onMessage(JSON.parse(event.data))
      } catch (e) {
        console.error('WS parse error', e)
      }
    }

    ws.onclose = () => {
      onDisconnect?.()
      clearInterval(pingInterval)
      setTimeout(connect, 3000)
    }

    ws.onerror = (e) => console.error('WS error', e)
  }

  connect()
  return () => { clearInterval(pingInterval); ws?.close() }
}
