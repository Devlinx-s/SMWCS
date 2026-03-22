import { useQuery } from '@tanstack/react-query'
import { fleetApi } from '../api'

export default function Drivers() {
  const { data: drivers, isLoading } = useQuery({
    queryKey: ['drivers'],
    queryFn:  () => fleetApi.getDrivers().then(r => r.data),
  })

  const { data: shifts } = useQuery({
    queryKey:       ['shifts'],
    queryFn:        () => fleetApi.getShifts().then(r => r.data),
    refetchInterval: 30000,
  })

  if (isLoading) return <div className="loading">Loading drivers…</div>

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-title">Drivers</div>
          <div className="page-sub">{drivers?.length ?? 0} drivers registered</div>
        </div>
      </div>

      <div className="card">
        <div className="card-title">Driver Roster</div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Phone</th>
                <th>Email</th>
                <th>License</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {drivers?.map(d => (
                <tr key={d.id}>
                  <td style={{ fontFamily: 'monospace', color: 'var(--text-2)' }}>{d.employee_id}</td>
                  <td style={{ fontWeight: 500 }}>{d.first_name} {d.last_name}</td>
                  <td style={{ color: 'var(--text-2)' }}>{d.phone || '—'}</td>
                  <td style={{ color: 'var(--text-2)', fontSize: 12 }}>{d.email || '—'}</td>
                  <td style={{ color: 'var(--text-2)', fontFamily: 'monospace', fontSize: 12 }}>
                    {d.license_number || '—'}
                  </td>
                  <td>
                    <span className={`badge badge-${d.status === 'active' ? 'green' : 'gray'}`}>
                      {d.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card">
        <div className="card-title">Recent Shifts</div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Shift ID</th>
                <th>Planned Start</th>
                <th>Planned End</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {shifts?.slice(0, 20).map(s => (
                <tr key={s.id}>
                  <td style={{ fontFamily: 'monospace', fontSize: 12, color: 'var(--text-2)' }}>
                    {s.id.slice(0, 8)}…
                  </td>
                  <td style={{ color: 'var(--text-2)', fontSize: 12 }}>
                    {new Date(s.planned_start).toLocaleString('en-KE')}
                  </td>
                  <td style={{ color: 'var(--text-2)', fontSize: 12 }}>
                    {new Date(s.planned_end).toLocaleString('en-KE')}
                  </td>
                  <td>
                    <span className={`badge badge-${
                      s.status === 'active'    ? 'teal'  :
                      s.status === 'completed' ? 'green' :
                      s.status === 'scheduled' ? 'blue'  : 'gray'
                    }`}>{s.status}</span>
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
