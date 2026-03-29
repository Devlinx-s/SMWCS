// Change this to your server IP when testing on a real device
// Use your machine's local IP, not localhost (Expo runs on a real device)
const SERVER_IP = '192.168.0.105'  // ← CHANGE THIS to your machine's IP

export const API_BASE    = `http://${SERVER_IP}`
export const AUTH_URL    = `${API_BASE}:8001`
export const TERMINAL_WS = `ws://${SERVER_IP}:8005`

export const COLORS = {
  bg:        '#0D1F3C',
  surface:   '#1A2D4A',
  surface2:  '#243550',
  teal:      '#006D77',
  teal_light:'#E0F4F6',
  green:     '#22C55E',
  red:       '#EF4444',
  amber:     '#F59E0B',
  white:     '#F0F4F8',
  gray:      '#8B90A7',
  gray_dark: '#3D5A80',
  navy:      '#0D1F3C',
}

export const FONTS = {
  bold:    'System',
  regular: 'System',
}
