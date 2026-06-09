import { DASHBOARD_HTML_URL } from '@/lib/blob-url'

export const dynamic = 'force-dynamic'

export default function Home() {
  if (!DASHBOARD_HTML_URL) {
    return (
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        height: '100vh', background: '#0d1520', color: '#b69d74',
        fontFamily: 'Montserrat, sans-serif', fontSize: 16, textAlign: 'center',
        padding: 40,
      }}>
        <div>
          <div style={{ fontSize: 28, fontWeight: 700, marginBottom: 12 }}>Douro Capital</div>
          <div style={{ color: '#6b8fa8' }}>
            Execute <code style={{ color: '#2fa874' }}>Oveview Crédito.py</code> para gerar e publicar o dashboard.
          </div>
        </div>
      </div>
    )
  }

  return (
    <iframe
      src={DASHBOARD_HTML_URL}
      style={{
        position: 'fixed',
        inset: 0,
        width: '100%',
        height: '100%',
        border: 'none',
        margin: 0,
        padding: 0,
        display: 'block',
      }}
      title="Overview Crédito — Douro Capital"
    />
  )
}
