import { create } from 'zustand'

// Simple in-memory store — works in Expo Go without native modules
let _token   = null
let _truckId = null

export const useAuthStore = create((set) => ({
  token:   null,
  driver:  null,
  truckId: null,

  setAuth: async (token, driver, truckId) => {
    _token   = token
    _truckId = truckId
    try {
      const AS = require('@react-native-async-storage/async-storage').default
      await AS.setItem('smwcs_driver_token',    token)
      await AS.setItem('smwcs_driver_truck_id', truckId)
    } catch (e) {
      console.log('AsyncStorage unavailable — using memory only')
    }
    set({ token, driver, truckId })
  },

  loadAuth: async () => {
    try {
      const AS    = require('@react-native-async-storage/async-storage').default
      const token   = await AS.getItem('smwcs_driver_token')
      const truckId = await AS.getItem('smwcs_driver_truck_id')
      if (token && truckId) {
        _token   = token
        _truckId = truckId
        set({ token, truckId })
        return { token, truckId }
      }
    } catch (e) {
      console.log('AsyncStorage unavailable')
    }
    return { token: _token, truckId: _truckId }
  },

  logout: async () => {
    _token   = null
    _truckId = null
    try {
      const AS = require('@react-native-async-storage/async-storage').default
      await AS.removeItem('smwcs_driver_token')
      await AS.removeItem('smwcs_driver_truck_id')
    } catch (e) {}
    set({ token: null, driver: null, truckId: null })
  },
}))

export const useRouteStore = create((set, get) => ({
  route:          null,
  currentStopIdx: 0,
  wsConnected:    false,
  offlineQueue:   [],
  pendingAlert:   null,

  setRoute:     (route) => set({ route, currentStopIdx: 0 }),
  setConnected: (v)     => set({ wsConnected: v }),

  getCurrentStop: () => {
    const { route, currentStopIdx } = get()
    return route?.stops?.[currentStopIdx] || null
  },

  markStopDone: (stopId) => set((state) => {
    const stops   = (state.route?.stops || []).map(s =>
      s.stop_id === stopId ? { ...s, completed: true } : s
    )
    const nextIdx = stops.findIndex(s => !s.completed)
    return {
      route:          { ...state.route, stops },
      currentStopIdx: nextIdx >= 0 ? nextIdx : state.currentStopIdx,
    }
  }),

  queueMessage: (msg) => set((state) => ({
    offlineQueue: [...state.offlineQueue, msg],
  })),

  getQueue:   () => get().offlineQueue,
  clearQueue: () => set({ offlineQueue: [] }),
}))
