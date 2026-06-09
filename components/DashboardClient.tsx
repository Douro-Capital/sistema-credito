'use client'

import { useEffect } from 'react'

export interface DashboardData {
  ativos: unknown[]
  fin_series: Record<string, unknown>
  rank_corp: unknown[]
  rank_bancos: unknown[]
  spreads_ts: Record<string, unknown>
  perf_data: unknown
  bonds_info: unknown[]
  bonds_ts: Record<string, unknown>
  setores: string[]
  pl_total: number
  pl_por_carteira: Record<string, number>
  news_data: unknown
  alertas: unknown[]
  fatos_relevantes: unknown[]
  bcb_live: Record<string, unknown>
  build_info: unknown
  carteiras: string[]
  officers: string[]
  logo_html: string
}

declare global {
  interface Window {
    ATIVOS: unknown
    FIN_SERIES: unknown
    RANK_CORP: unknown
    RANK_BANCOS: unknown
    SPREADS_TS: unknown
    PERF_DATA: unknown
    BONDS_INFO: unknown
    BONDS_TS: unknown
    setores: unknown
    PL_TOTAL: unknown
    PL_POR_CARTEIRA: unknown
    NEWS_DATA: unknown
    ALERTAS_NOTIF: unknown
    FATOS_RELEVANTES: unknown
    SCORECARD_SRC: unknown
    BCB_LIVE: unknown
    BUILD_INFO: unknown
    COLORS: string[]
    showPage: (id: string, el: HTMLElement | null) => void
    buildHome: () => void
    initDashboard: () => void
  }
}

export default function DashboardClient({ data }: { data: DashboardData }) {
  useEffect(() => {
    // ── Injeta todas as variáveis globais que o dashboard-init.js espera ──
    window.ATIVOS             = data.ativos
    window.FIN_SERIES         = data.fin_series
    window.RANK_CORP          = data.rank_corp
    window.RANK_BANCOS        = data.rank_bancos
    window.SPREADS_TS         = data.spreads_ts
    window.PERF_DATA          = data.perf_data
    window.BONDS_INFO         = data.bonds_info
    window.BONDS_TS           = data.bonds_ts
    window.setores            = data.setores
    window.PL_TOTAL           = data.pl_total
    window.PL_POR_CARTEIRA    = data.pl_por_carteira
    window.NEWS_DATA          = data.news_data
    window.ALERTAS_NOTIF      = data.alertas
    window.FATOS_RELEVANTES   = data.fatos_relevantes
    window.SCORECARD_SRC      = '/scorecard.html'
    window.BCB_LIVE           = data.bcb_live
    window.BUILD_INFO         = data.build_info

    // ── Dispara a inicialização do dashboard após variáveis estarem prontas ──
    if (typeof window.initDashboard === 'function') {
      window.initDashboard()
    } else {
      // dashboard-init.js ainda está carregando — aguarda
      const interval = setInterval(() => {
        if (typeof window.initDashboard === 'function') {
          clearInterval(interval)
          window.initDashboard()
        }
      }, 100)
      // Timeout de segurança
      setTimeout(() => clearInterval(interval), 10000)
    }
  }, [data])

  // Opções dos dropdowns construídas a partir dos dados
  const carteirasOpts = (data.carteiras ?? []).map((c: string) => (
    <div key={c} className="ss-opt" data-value={c}>{c}</div>
  ))
  const setoresOpts = (data.setores ?? []).map((s: string) => (
    <div key={s} className="ss-opt" data-value={s}>{s}</div>
  ))
  const officersOpts = (data.officers ?? []).map((o: string) => (
    <div key={o} className="ss-opt" data-value={o}>{o}</div>
  ))

  return (
    <>
      {/* ══════════════════════════════════════════════════════ */}
      {/*  SIDEBAR                                              */}
      {/* ══════════════════════════════════════════════════════ */}
      <aside className="sidebar">
        <div className="sidebar-logo" style={{ justifyContent: 'center', padding: '24px 20px' }}>
          <div dangerouslySetInnerHTML={{ __html: data.logo_html }} />
        </div>

        <div className="nav-section">Carteira</div>
        <div className="nav-item active" onClick={() => window.showPage?.('composicao', null)}>
          <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/>
            <rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>
          </svg>
          <span>Composição</span>
        </div>
        <div className="nav-item" onClick={() => window.showPage?.('rating', null)}>
          <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
          </svg>
          <span>Classe e Rating</span>
        </div>
        <div className="nav-item" onClick={() => window.showPage?.('performance', null)}>
          <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M3 17l6-6 4 4 7-7"/>
          </svg>
          <span>Performance</span>
        </div>

        <div className="nav-section">Mercado</div>
        <div className="nav-item" onClick={() => window.showPage?.('spreads', null)}>
          <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M3 3v18h18"/><path d="M18 17l-5-5-4 4-3-3"/>
          </svg>
          <span>Spreads</span>
        </div>
        <div className="nav-item" onClick={() => window.showPage?.('tunel', null)}>
          <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z"/>
          </svg>
          <span>Túnel de Preço</span>
        </div>
        <div className="nav-item" onClick={() => window.showPage?.('bonds', null)}>
          <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M2 12h4l2-9 5 18 2-9h5"/>
          </svg>
          <span>Bonds</span>
        </div>

        <div className="nav-section">Fundamentos Financeiros</div>
        <div className="nav-item" onClick={() => window.showPage?.('financeiros', null)}>
          <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
          </svg>
          <span>Dados</span>
        </div>
        <div className="nav-item" onClick={() => window.showPage?.('fundamentos', null)}>
          <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/>
          </svg>
          <span>Empresas</span>
        </div>
        <div className="nav-item" onClick={() => window.showPage?.('bancos', null)}>
          <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/><path d="M2 11h20"/>
          </svg>
          <span>Bancos</span>
        </div>

        <div className="nav-section">RANKING</div>
        <div className="nav-item" onClick={() => window.showPage?.('ranking', null)}>
          <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M18 20V10M12 20V4M6 20v-6"/>
          </svg>
          <span>Ranking</span>
        </div>
        <div className="nav-item" onClick={() => window.showPage?.('scorecard', null)}>
          <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18"/><path d="M9 21V9"/>
          </svg>
          <span>Scorecard</span>
        </div>

        <div style={{ marginTop: 'auto', marginLeft: 12, marginRight: 12, marginBottom: 8, borderTop: '1px solid rgba(182,157,116,.25)', paddingTop: 8 }} />

        {/* Notificações */}
        <div
          className="nav-item nav-notif"
          id="navNotifItem"
          onClick={() => window.showPage?.('notificacoes', null)}
          style={{ margin: '4px 8px 6px', borderRadius: 10, background: 'linear-gradient(145deg,rgba(47,168,116,.16) 0%,rgba(0,103,123,.10) 55%,rgba(47,168,116,.12) 100%)', border: '1px solid rgba(47,168,116,.28)', borderTopColor: 'rgba(60,210,140,.35)', position: 'relative', overflow: 'hidden', boxShadow: '0 4px 16px rgba(47,168,116,.12)' }}
        >
          <div style={{ position: 'absolute', inset: 0, background: 'radial-gradient(ellipse at 80% 50%,rgba(47,168,116,.08),transparent 70%)', pointerEvents: 'none' }} />
          <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="#3cd28a" strokeWidth="2" style={{ flexShrink: 0, zIndex: 1 }}>
            <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
            <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
          </svg>
          <span style={{ color: '#3cd28a', fontWeight: 700, letterSpacing: '.02em', display: 'flex', alignItems: 'center', gap: 6, zIndex: 1 }}>
            Notificações
            <span id="notifBadgeNav" style={{ display: 'none', background: 'linear-gradient(135deg,#2fa874,#3cd28a)', color: '#0d1f17', fontSize: 8, fontWeight: 800, padding: '2px 6px', borderRadius: 4, letterSpacing: '.05em' }} />
          </span>
        </div>

        {/* Douro News */}
        <div
          className="nav-item nav-news"
          onClick={() => window.showPage?.('douro-news', null)}
          style={{ margin: '4px 8px 24px', borderRadius: 10, background: 'linear-gradient(145deg,rgba(182,157,116,.18) 0%,rgba(182,157,116,.08) 55%,rgba(182,157,116,.14) 100%)', border: '1px solid rgba(182,157,116,.32)', borderTopColor: 'rgba(212,180,122,.45)', position: 'relative', overflow: 'hidden', boxShadow: '0 4px 16px rgba(182,157,116,.15)' }}
        >
          <div className="news-icon-wrap">
            <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="#d4b47a" strokeWidth="2">
              <path d="M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16a2 2 0 0 1-2 2zm0 0a2 2 0 0 1-2-2v-9c0-1.1.9-2 2-2h2"/>
              <line className="news-headline-line" x1="10" y1="7" x2="18" y2="7" stroke="#d4b47a" strokeWidth="1.5"/>
              <line className="news-headline-line" x1="10" y1="10" x2="16" y2="10" stroke="#d4b47a" strokeWidth="1.5" opacity=".6"/>
              <line className="news-headline-line" x1="10" y1="13" x2="17" y2="13" stroke="#d4b47a" strokeWidth="1.5" opacity=".7"/>
              <line x1="10" y1="17" x2="15" y2="17" stroke="#d4b47a" strokeWidth="1.5" opacity=".4"/>
            </svg>
          </div>
          <span style={{ color: '#d4b47a', fontWeight: 700, letterSpacing: '.02em', display: 'flex', alignItems: 'center', gap: 6 }}>
            <span className="news-label">Douro News</span>
            <span className="news-badge" style={{ background: 'linear-gradient(135deg,#b69d74,#d4b47a)', color: '#1f2839', fontSize: 8, fontWeight: 800, padding: '2px 6px', borderRadius: 4, letterSpacing: '.05em', display: 'inline-block' }}>NEWS</span>
          </span>
        </div>
      </aside>

      {/* ══════════════════════════════════════════════════════ */}
      {/*  MAIN                                                 */}
      {/* ══════════════════════════════════════════════════════ */}
      <main className="main">

        {/* ── TOPBAR ── */}
        <div className="topbar">
          <div className="topbar-wave" aria-hidden="true">
            <svg viewBox="0 0 1440 40" fill="none" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="none">
              <path d="M0 28 C240 8 480 38 720 22 C960 6 1200 36 1440 18 L1440 40 L0 40 Z" fill="#1f2839"/>
              <path d="M0 34 C180 18 360 38 540 28 C720 18 900 38 1080 26 C1260 14 1380 32 1440 24 L1440 40 L0 40 Z" fill="#b69d74" opacity=".5"/>
            </svg>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <button
              className="home-btn"
              id="homeBtnTopbar"
              onClick={() => window.showPage?.('home', null)}
              title="Página Inicial"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                <path d="M3 9.5L12 3l9 6.5V20a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V9.5z"/>
                <path d="M9 21V12h6v9"/>
              </svg>
            </button>
            <button id="sidebarPinBtn" className="sidebar-pin-btn" title="Fixar painel lateral">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                <line x1="12" y1="17" x2="12" y2="22"/>
                <path d="M5 17h14v-1.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V6h1a2 2 0 0 0 0-4H8a2 2 0 0 0 0 4h1v4.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24Z"/>
              </svg>
            </button>
            <div className="topbar-title">Overview <span>Crédito</span></div>
          </div>

          <div className="topbar-right">
            {/* ── Filtro Carteira ── */}
            <div className="filter-pill" id="ss-carteira" data-prefix="Carteira: " data-all="Todas">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="1" y="4" width="22" height="16" rx="2"/>
              </svg>
              <span className="ss-label">Carteira: Todas</span>
              <svg className="ss-caret" width="10" height="6" viewBox="0 0 10 6" fill="none">
                <polyline points="1,1 5,5 9,1" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              <div className="ss-dropdown" onClick={(e) => e.stopPropagation()}>
                <input className="ss-search" type="text" placeholder="Buscar carteira..." />
                <div className="ss-list">
                  <div className="ss-opt ss-active" data-value="">Todas</div>
                  {carteirasOpts}
                </div>
              </div>
              <select id="carteiraFilter" style={{ display: 'none' }}>
                <option value="">Todas</option>
                {(data.carteiras ?? []).map((c: string) => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>

            {/* ── Filtro Setor ── */}
            <div className="filter-pill" id="ss-setor" data-prefix="Setor: " data-all="Todos">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
              </svg>
              <span className="ss-label">Setor: Todos</span>
              <svg className="ss-caret" width="10" height="6" viewBox="0 0 10 6" fill="none">
                <polyline points="1,1 5,5 9,1" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              <div className="ss-dropdown" onClick={(e) => e.stopPropagation()}>
                <input className="ss-search" type="text" placeholder="Buscar setor..." />
                <div className="ss-list">
                  <div className="ss-opt ss-active" data-value="">Todos</div>
                  {setoresOpts}
                </div>
              </div>
              <select id="setorFilter" style={{ display: 'none' }}>
                <option value="">Todos</option>
                {(data.setores ?? []).map((s: string) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>

            {/* ── Filtro Officer ── */}
            <div className="filter-pill" id="ss-officer" data-prefix="Officer: " data-all="Todos">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
              </svg>
              <span className="ss-label">Officer: Todos</span>
              <svg className="ss-caret" width="10" height="6" viewBox="0 0 10 6" fill="none">
                <polyline points="1,1 5,5 9,1" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              <div className="ss-dropdown" onClick={(e) => e.stopPropagation()}>
                <input className="ss-search" type="text" placeholder="Buscar officer..." />
                <div className="ss-list">
                  <div className="ss-opt ss-active" data-value="">Todos</div>
                  {officersOpts}
                </div>
              </div>
              <select id="officerFilter" style={{ display: 'none' }}>
                <option value="">Todos</option>
                {(data.officers ?? []).map((o: string) => <option key={o} value={o}>{o}</option>)}
              </select>
            </div>
          </div>
        </div>

        {/* ── BOTÃO (i) FLUTUANTE ── */}
        <button
          id="sysInfoBtn"
          title="Como este sistema funciona"
          style={{ position: 'fixed', bottom: 12, left: 12, zIndex: 9990, width: 18, height: 18, borderRadius: 4, background: 'transparent', border: '1px solid rgba(182,157,116,.22)', color: 'rgba(182,157,116,.38)', fontSize: 9, fontWeight: 700, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', transition: 'all .2s', fontFamily: "'DM Mono',monospace", letterSpacing: 0, opacity: .55 }}
        >
          i
        </button>

        {/* ══════════════════════════════════════════════════════ */}
        {/*  PÁGINAS — containers que o JS popula                 */}
        {/* ══════════════════════════════════════════════════════ */}

        {/* HOME */}
        <div id="page-home" className="page content" />

        {/* COMPOSIÇÃO */}
        <div id="page-composicao" className="page content" />

        {/* CLASSE E RATING */}
        <div id="page-rating" className="page content" />

        {/* PERFORMANCE */}
        <div id="page-performance" className="page content" />

        {/* SPREADS */}
        <div id="page-spreads" className="page content" />

        {/* TÚNEL DE PREÇO */}
        <div id="page-tunel" className="page content" />

        {/* BONDS */}
        <div id="page-bonds" className="page content" />

        {/* DADOS FINANCEIROS */}
        <div id="page-financeiros" className="page content" />

        {/* FUNDAMENTOS */}
        <div id="page-fundamentos" className="page content" />

        {/* BANCOS */}
        <div id="page-bancos" className="page content" />

        {/* DOURO NEWS */}
        <div id="page-douro-news" className="page content" />

        {/* NOTIFICAÇÕES */}
        <div id="page-notificacoes" className="page content" />

        {/* RANKING */}
        <div id="page-ranking" className="page content" />

        {/* SCORECARD */}
        <div id="page-scorecard" className="page content" />

        {/* ── MODAL: COMO O SISTEMA FUNCIONA ── */}
        <div id="sysInfoModal" style={{ display: 'none', position: 'fixed', inset: 0, zIndex: 10000, background: 'rgba(15,20,35,.6)', backdropFilter: 'blur(16px)', alignItems: 'center', justifyContent: 'center' }} />

        {/* ── DOURADO CHATBOT ── */}
        <button id="douradoBtn" title="Dourado — Assistente de Crédito">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#1f2839" strokeWidth="2.2">
            <path d="M12 2C6.48 2 2 6.48 2 12c0 1.54.36 2.98.97 4.29L2 22l5.71-.97A9.953 9.953 0 0012 22c5.52 0 10-4.48 10-10S17.52 2 12 2z"/>
          </svg>
        </button>

        {/* ── PAINEL DOURADO ── */}
        <div id="douradoPanel">
          <div className="dourado-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div className="dourado-avatar">D</div>
              <div>
                <div style={{ fontSize: 12, fontWeight: 700, color: '#d4b47a', letterSpacing: '.02em' }}>Dourado</div>
                <div style={{ fontSize: 10, color: '#3a4f6a', marginTop: 1 }}>Assistente de Crédito</div>
              </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div className="dourado-status" />
              <button
                onClick={() => {
                  const p = document.getElementById('douradoPanel')
                  p?.classList.remove('open')
                }}
                style={{ background: 'none', border: 'none', color: '#3a4f6a', cursor: 'pointer', fontSize: 18, lineHeight: 1 }}
              >×</button>
            </div>
          </div>
          <div className="dourado-msgs" id="douradoMsgs" />
          <div className="dourado-chips" id="douradoChips" />
          <div className="dourado-input-row">
            <textarea
              id="douradoInput"
              className="dourado-input"
              placeholder="Pergunte sobre a carteira..."
              rows={1}
            />
            <button
              className="dourado-send"
              onClick={() => {
                if (typeof (window as unknown as Record<string, unknown>).douradoSend === 'function') {
                  (window as unknown as Record<string, () => void>).douradoSend()
                }
              }}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#1f2839" strokeWidth="2.5">
                <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
              </svg>
            </button>
          </div>
        </div>

      </main>
    </>
  )
}
