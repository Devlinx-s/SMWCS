import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { commandApi } from '../api'
import toast from 'react-hot-toast'

const severityColor = { critical: 'red', high: 'amber', medium: 'blue', low: 'gray' }

function timeAgo(iso) {
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1)  return 'just now'
  if (mins < 60) return `${mins}m ago`
  return `${Math.floor(mins / 60)}h ago`
}

export default function Alerts() {
  const [filter, setFilter] = useState('open')
  const qc = useQueryClient()

  const { data: alerts, isLoading } = useQuery({
    queryKey:       ['alerts', filter],
    queryFn:        () => commandApi.getAlerts({
      resolved: filter === 'resolved' ? true : filter === 'open' ? false : undefined,
      limit: 100,
    }).then(r => r.data),
    refetchInterval: 10000,
  })

  const { data: stats } = useQuery({
    queryKey:       ['alert-stats'],
    queryFn:        () => commandApi.getAlertStats().then(r => r.data),
    refetchInterval: 10000,
  })

  const acknowledge = async (id) => {
    try {
      await commandApi.acknowledgeAlert(id)
      toast.success('Acknowledged')
      qc.invalidateQueries({ queryKey: ['alerts'] })
      qc.invalidateQueries({ queryKey: ['alert-stats'] })
    } catch {
      toast.error('Failed')
    }
  }

  const resolve = async (id) => {
    try {
      await commandApi.resolveAlert(id)
      toast.success('Resolved')
      qc.invalidateQueries({ queryKey: ['alerts'] })
      qc.invalidateQueries({ queryKey: ['alert-stats'] })
    } catch {
      toast.error('Failed')
    }
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-title">Alert Center</div>
          <div className="page-sub">{stats?.open ?? 0} open · {stats?.critical ?? 0} critical</div>
        </div>
      </div>

      {/* Stats */}
      <div className="stats-grid" style={{ marginBottom: 20 }}>
        {[
          { label: 'Critical', value: stats?.critical ?? 0, cls: 'red' },
          { label: 'High',     value: stats?.high     ?? 0, cls: 'amber' },
          { label: 'Medium',   value: stats?.medium   ?? 0, cls: 'blue' },
          { label: 'Low',      value: stats?.low      ?? 0, cls: 'gray' },
          { label: 'Resolved', value: stats?.resolved ?? 0, cls: 'green' },
        ].map(s => (
          <div key={s.label} className="stat-card">
            <div className="stat-label">{s.label}</div>
            <div className={`stat-value ${s.cls}`}>{s.value}</div>
          </div>
        ))}
      </div>

      {/* Filter */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        {['open', 'all', 'resolved'].map(f => (
          <button
            key={f}
            className={`btn${filter === f ? ' btn-primary' : ''}`}
            onClick={() => setFilter(f)}
            style={{ textTransform: 'capitalize' }}
          >
            {f}
          </button>
        ))}
      </div>

      <div className="card">
        {isLoading && <div className="loading">Loading alerts…</div>}
        {!isLoading && alerts?.length === 0 && (
          <div className="empty">No alerts</div>
        )}
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Severity</th>
                <th>Type</th>
                <th>Message</th>
                <th>Sensor / Truck</th>
                <th>Time</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {alerts?.map(a => (
                <tr key={a.id}>
                  <td>
                    <span className={`badge badge-${severityColor[a.severity] || 'gray'}`}>
                      {a.severity}
                    </span>
                  </td>
                  <td style={{ color: 'var(--text-2)', fontSize: 12 }}>
                    {a.type.replace(/_/g, ' ')}
                  </td>
                  <td>{a.message}</td>
                  <td style={{ color: 'var(--text-2)', fontSize: 12, fontFamily: 'monospace' }}>
                    {a.sensor_id || a.truck_id || '—'}
                  </td>
                  <td style={{ color: 'var(--text-3)', fontSize: 12 }}>
                    {timeAgo(a.created_at)}
                  </td>
                  <td>
                    <div style={{ display: 'flex', gap: 6 }}>
                      {!a.acknowledged && (
                        <button className="btn" style={{ fontSize: 11, padding: '3px 8px' }}
                          onClick={() => acknowledge(a.id)}>ACK</button>
                      )}
                      {!a.resolved && (
                        <button className="btn btn-danger" style={{ fontSize: 11, padding: '3px 8px' }}
                          onClick={() => resolve(a.id)}>Resolve</button>
                      )}
                      {a.resolved && (
                        <span style={{ color: 'var(--green)', fontSize: 12 }}>✓ Resolved</span>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
