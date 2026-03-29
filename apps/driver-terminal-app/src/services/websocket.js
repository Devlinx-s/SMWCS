import { TERMINAL_WS } from '../config'
import { useRouteStore } from '../store/useStore'

let ws          = null
let reconnectT  = null
let currentTruckId = null
let shouldReconnect = false

export function initWS(truckId) {
  currentTruckId  = truckId
  shouldReconnect = true
  connect()
}

function connect() {
  if (!shouldReconnect || !currentTruckId) return
  if (ws) { try { ws.close() } catch (_) {} }

  const url = `${TERMINAL_WS}/ws/terminal/${currentTruckId}?token=driver-app-token`
  ws = new WebSocket(url)

  ws.onopen = () => {
    console.log('Terminal WS connected')
    useRouteStore.getState().setConnected(true)
    // Flush offline queue
    const queue = useRouteStore.getState().getQueue()
    for (const msg of queue) {
      try { ws.send(JSON.stringify(msg)) } catch (_) {}
    }
    useRouteStore.getState().clearQueue()
  }

  ws.onmessage = (event) => {
    try {
      handleMessage(JSON.parse(event.data))
    } catch (e) {
      console.error('WS parse error', e)
    }
  }

  ws.onclose = () => {
    useRouteStore.getState().setConnected(false)
    if (!shouldReconnect) return
    console.log('WS disconnected — reconnecting in 4s')
    clearTimeout(reconnectT)
    reconnectT = setTimeout(connect, 4000)
  }

  ws.onerror = () => {}
}

function handleMessage(msg) {
  const store = useRouteStore.getState()
  switch (msg.type) {
    case 'ROUTE_FULL':
    case 'ROUTE_DELTA':
      if (msg.route) store.setRoute(msg.route)
      break
    case 'STOP_CONFIRMED':
      store.markStopDone(msg.stop_id)
      break
    case 'DRIVER_ALERT':
      useRouteStore.setState({ pendingAlert: msg.alert })
      break
  }
}

export function sendMessage(msg) {
  if (ws?.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(msg))
  } else {
    useRouteStore.getState().queueMessage(msg)
  }
}

export function disconnectWS() {
  shouldReconnect = false
  currentTruckId  = null
  clearTimeout(reconnectT)
  if (ws) {
    try { ws.close() } catch (_) {}
    ws = null
  }
  useRouteStore.getState().setConnected(false)
  useRouteStore.getState().setRoute(null)
}
