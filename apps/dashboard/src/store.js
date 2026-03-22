import { create } from 'zustand'

export const useAuthStore = create((set) => ({
  token: localStorage.getItem('smwcs_token') || null,
  user:  null,

  setAuth: (token, user) => {
    localStorage.setItem('smwcs_token', token)
    set({ token, user })
  },

  logout: () => {
    localStorage.removeItem('smwcs_token')
    set({ token: null, user: null })
  },
}))

export const useWsStore = create((set) => ({
  connected:      false,
  livePositions:  {},
  liveAlerts:     [],

  setConnected: (v) => set({ connected: v }),

  handleMessage: (msg) => {
    if (msg.type === 'TRUCK_POSITION') {
      set((state) => ({
        livePositions: {
          ...state.livePositions,
          [msg.data.truck_id]: msg.data,
        },
      }))
    } else if (msg.type === 'ALERT_CREATED') {
      set((state) => ({
        liveAlerts: [msg.data, ...state.liveAlerts].slice(0, 50),
      }))
    }
  },
}))
