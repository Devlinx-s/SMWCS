import { useQuery } from '@tanstack/react-query'
import { fleetApi } from '../api'

export default function Fleet() {
  const { data: trucks, isLoading } = useQuery({
    queryKey:       ['trucks'],
    queryFn:        () => fleetApi.getTrucks().then(r => r.data),
    refetchInterval: 15000,
  })

  const { data: drivers } = useQuery({
    queryKey: ['drivers'],
    queryFn:  () => fleetApi.getDrivers().then(r => r.data),
  })

  if (isLoading) return <div className="loading">Loading fleet…</div>

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-title">Fleet Management</div>
          <div className="page-sub">{trucks?.length ?? 0} trucks registered</div>
        </div>
      </div>

      <div className="card">
        <div className="card-title">Trucks</div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Registration</th>
                <th>Make / Model</th>
                <th>Status</th>
                <th>Capacity</th>
                <th>Load</th>
                <th>Fuel</th>
              </tr>
            </thead>
            <tbody>
              {trucks?.map(t => (
                <tr key={t.id}>
                  <td style={{ fontWeight: 600 }}>{t.registration}</td>
                  <td style={{ color: 'var(--text-2)' }}>
                    {t.make} {t.model} {t.year && `(${t.year})`}
                  </td>
                  <td>
                    <span className={`badge badge-${
                      t.status === 'on_route'    ? 'teal'  :
                      t.status === 'available'   ? 'green' :
                      t.status === 'maintenance' ? 'amber' : 'gray'
                    }`}>{t.status}</span>
                  </td>
                  <td style={{ color: 'var(--text-2)' }}>{t.capacity_kg.toLocaleString()} kg</td>
                  <td>{t.current_load_kg.toLocaleString()} kg</td>
                  <td>
                    <span className="badge badge-gray">{t.fuel_type}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card">
        <div className="card-title">Drivers</div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Employee ID</th>
                <th>Name</th>
                <th>Phone</th>
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
                  <td style={{ color: 'var(--text-2)' }}>{d.license_number || '—'}</td>
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
    </div>
  )
}
