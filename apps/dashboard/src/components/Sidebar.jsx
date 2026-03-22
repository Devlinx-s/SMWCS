import { useAuthStore } from '../store'
import { useWsStore } from '../store'

const NAV = [
  { key: 'dashboard', icon: '📊', label: 'Dashboard' },
  { key: 'fleet',     icon: '🚛', label: 'Fleet' },
  { key: 'bins',      icon: '🗑️',  label: 'Bins' },
  { key: 'alerts',    icon: '🔔', label: 'Alerts' },
  { key: 'drivers',   icon: '👤', label: 'Drivers' },
]

export default function Sidebar({ active, onChange }) {
  const user      = useAuthStore(s => s.user)
  const logout    = useAuthStore(s => s.logout)
  const connected = useWsStore(s => s.connected)

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <h1>🗑️ SMWCS</h1>
        <p>Command Center — Nairobi</p>
      </div>

      <nav className="sidebar-nav">
        <div className="nav-label">Navigation</div>
        {NAV.map(item => (
          <button
            key={item.key}
            className={`nav-item${active === item.key ? ' active' : ''}`}
            onClick={() => onChange(item.key)}
          >
            <span className="nav-icon">{item.icon}</span>
            {item.label}
          </button>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div style={{ marginBottom: 8 }}>
          <span className={connected ? 'ws-connected' : 'ws-disconnected'}>
            {connected ? '● Live' : '○ Offline'}
          </span>
        </div>
        {user && (
          <div style={{ marginBottom: 8, color: 'var(--text-2)' }}>
            {user.first_name} {user.last_name}
            <div style={{ fontSize: 11, color: 'var(--text-3)' }}>{user.role}</div>
          </div>
        )}
        <button className="btn" onClick={logout} style={{ width: '100%', fontSize: 12 }}>
          Sign out
        </button>
      </div>
    </aside>
  )
}
