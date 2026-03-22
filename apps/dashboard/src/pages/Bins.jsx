import { useQuery } from '@tanstack/react-query'
import { binsApi } from '../api'

export default function Bins() {
  const { data: bins, isLoading } = useQuery({
    queryKey:       ['bins'],
    queryFn:        () => binsApi.getBins({ per_page: 100 }).then(r => r.data),
    refetchInterval: 30000,
  })

  const { data: zones } = useQuery({
    queryKey: ['zones'],
    queryFn:  () => binsApi.getZones().then(r => r.data),
  })

  const zoneMap = {}
  zones?.forEach(z => { zoneMap[z.id] = z.name })

  if (isLoading) return <div className="loading">Loading bins…</div>

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-title">Bin Registry</div>
          <div className="page-sub">{bins?.length ?? 0} bins registered</div>
        </div>
      </div>

      <div className="stats-grid" style={{ marginBottom: 20 }}>
        <div className="stat-card">
          <div className="stat-label">Total bins</div>
          <div className="stat-value">{bins?.length ?? 0}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Active</div>
          <div className="stat-value green">
            {bins?.filter(b => b.status === 'active').length ?? 0}
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Zones</div>
          <div className="stat-value teal">{zones?.length ?? 0}</div>
        </div>
      </div>

      <div className="card">
        <div className="card-title">All Bins</div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Serial</th>
                <th>Zone</th>
                <th>Address</th>
                <th>Capacity</th>
                <th>Status</th>
                <th>Sensor</th>
              </tr>
            </thead>
            <tbody>
              {bins?.map(b => (
                <tr key={b.id}>
                  <td style={{ fontFamily: 'monospace', fontWeight: 500 }}>{b.serial_number}</td>
                  <td style={{ color: 'var(--text-2)' }}>
                    {zoneMap[b.zone_id] || b.zone_id?.slice(0, 8) || '—'}
                  </td>
                  <td style={{ color: 'var(--text-2)', fontSize: 12 }}>{b.address || '—'}</td>
                  <td style={{ color: 'var(--text-2)' }}>{b.capacity_litres}L</td>
                  <td>
                    <span className={`badge badge-${b.status === 'active' ? 'green' : 'amber'}`}>
                      {b.status}
                    </span>
                  </td>
                  <td style={{ color: 'var(--text-2)', fontSize: 12 }}>
                    {b.sensor_id || <span style={{ color: 'var(--text-3)' }}>No sensor</span>}
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
