import { useState, useEffect } from 'react'
import { useAuthStore, useWsStore } from './store'
import { createDashboardWS } from './api'
import Sidebar   from './components/Sidebar'
import Login     from './pages/Login'
import Dashboard from './pages/Dashboard'
import Fleet     from './pages/Fleet'
import Bins      from './pages/Bins'
import Alerts    from './pages/Alerts'
import Drivers   from './pages/Drivers'

const PAGES = { dashboard: Dashboard, fleet: Fleet, bins: Bins, alerts: Alerts, drivers: Drivers }

export default function App() {
  const token        = useAuthStore(s => s.token)
  const [page, setPage] = useState('dashboard')
  const setConnected = useWsStore(s => s.setConnected)
  const handleMsg    = useWsStore(s => s.handleMessage)

  useEffect(() => {
    if (!token) return
    const cleanup = createDashboardWS(
      (msg) => handleMsg(msg),
      ()    => setConnected(true),
      ()    => setConnected(false),
    )
    return cleanup
  }, [token])

  if (!token) return <Login onLogin={() => setPage('dashboard')} />

  const Page = PAGES[page] || Dashboard

  return (
    <div className="app">
      <Sidebar active={page} onChange={setPage} />
      <main className="main">
        <Page />
      </main>
    </div>
  )
}
