import { useQuery } from '@tanstack/react-query'
import { commandApi } from '../api'
import toast from 'react-hot-toast'

function timeAgo(iso) {
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1)  return 'just now'
  if (mins < 60) return `${mins}m ago`
  return `${Math.floor(mins / 60)}h ago`
}

const severityColor = { critical: 'red', high: 'amber', medium: 'blue', low: 'gray' }

export default function Dashboard() {
  const { data: summary } = useQuery({
    queryKey: ['summary'],
    queryFn:  () => commandApi.getSummary().then(r => r.data),
    refetchInterval: 30000,
  })

  const { data: fleetStats } = useQuery({
    queryKey: ['fleet-stats'],
    queryFn:  () => commandApi.getFleetStats().then(r => r.data),
    refetchInterval: 15000,
  })

  const { data: alertStats } = useQuery({
    queryKey: ['alert-stats'],
    queryFn:  () => commandApi.getAlertStats().then(r => r.data),
    refetchInterval: 15000,
  })

  const { data: alerts } = useQuery({
    queryKey: ['alerts-recent'],
    queryFn:  () => commandApi.getAlerts({ resolved: false, limit: 10 }).then(r => r.data),
    refetchInterval: 10000,
  })

  const { data: fleet } = useQuery({
    queryKey: ['fleet-live'],
    queryFn:  () => commandApi.getFleetLive().then(r => r.data),
    refetchInterval: 15000,
  })

  const handleAcknowledge = async (id) => {
    try {
      await commandApi.acknowledgeAlert(id)
      toast.success('Alert acknowledged')
    } catch {
      toast.error('Failed to acknowledge')
    }
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-title">Command Dashboard</div>
          <div className="page-sub">Nairobi Waste Collection — Live Overview</div>
        </div>
        <div style={{ fontSize: 12, color: 'var(--text-3)' }}>
          {new Date().toLocaleString('en-KE', { timeZone: 'Africa/Nairobi' })}
        </div>
      </div>

      {/* Stats */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-label">Trucks on route</div>
          <div className="stat-value teal">{fleetStats?.on_route ?? '—'}</div>
          <div className="stat-sub">of {fleetStats?.total ?? '—'} total</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Available trucks</div>
          <div className="stat-value green">{fleetStats?.available ?? '—'}</div>
          <div className="stat-sub">ready to deploy</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Open alerts</div>
          <div className="stat-value red">{alertStats?.open ?? '—'}</div>
          <div className="stat-sub">{alertStats?.critical ?? 0} critical</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Active bins</div>
          <div className="stat-value">{summary?.bins?.bins_active ?? '—'}</div>
          <div className="stat-sub">of {summary?.bins?.bins_total ?? '—'} registered</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Active drivers</div>
          <div className="stat-value">{summary?.drivers?.drivers_active ?? '—'}</div>
          <div className="stat-sub">on duty</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">High alerts</div>
          <div className="stat-value amber">{alertStats?.high ?? '—'}</div>
          <div className="stat-sub">need attention</div>
        </div>
      </div>

      <div className="grid-2">
        {/* Active fleet */}
        <div className="card">
          <div className="card-title">Active Fleet</div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Truck</th>
                  <th>Driver</th>
                  <th>Status</th>
                  <th>Load</th>
                </tr>
              </thead>
              <tbody>
                {fleet?.map(t => (
                  <tr key={t.id}>
                    <td style={{ fontWeight: 500 }}>{t.registration}</td>
                    <td style={{ color: 'var(--text-2)' }}>
                      {t.driver_name || <span style={{ color: 'var(--text-3)' }}>Unassigned</span>}
                    </td>
                    <td>
                      <span className={`badge badge-${
                        t.status === 'on_route'    ? 'teal'  :
                        t.status === 'available'   ? 'green' :
                        t.status === 'maintenance' ? 'amber' : 'gray'
                      }`}>{t.status}</span>
                    </td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <div className="progress-bar" style={{ width: 60 }}>
                          <div
                            className="progress-fill"
                            style={{
                              width:      `${t.load_pct}%`,
                              background: t.load_pct > 80 ? 'var(--red)' :
                                          t.load_pct > 50 ? 'var(--amber)' : 'var(--green)',
                            }}
                          />
                        </div>
                        <span style={{ color: 'var(--text-2)', fontSize: 12 }}>
                          {t.load_pct}%
                        </span>
                      </div>
                    </td>
                  </tr>
                ))}
                {!fleet?.length && (
                  <tr><td colSpan={4} className="empty">No trucks registered</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Alert feed */}
        <div className="card">
          <div className="card-title">
            Live Alerts
            <span className="badge badge-red">{alertStats?.open ?? 0} open</span>
          </div>
          {alerts?.length === 0 && (
            <div className="empty">No open alerts</div>
          )}
          {alerts?.map(alert => (
            <div key={alert.id} className="alert-item">
              <div className={`alert-dot ${severityColor[alert.severity] || 'gray'}`} />
              <div style={{ flex: 1 }}>
                <div className="alert-msg">{alert.message}</div>
                <div className="alert-time">{timeAgo(alert.created_at)}</div>
              </div>
              {!alert.acknowledged && (
                <button
                  className="btn"
                  style={{ fontSize: 11, padding: '3px 8px' }}
                  onClick={() => handleAcknowledge(alert.id)}
                >
                  ACK
                </button>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
