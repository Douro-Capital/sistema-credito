import { readFileSync, existsSync } from 'fs'
import path from 'path'
import DashboardClient from '@/components/DashboardClient'

// Dados vazios usados quando dashboard.json ainda não foi gerado
const EMPTY_DATA = {
  ativos: [],
  fin_series: {},
  rank_corp: [],
  rank_bancos: [],
  spreads_ts: {},
  perf_data: { datas: [], ativos: {}, correlacao: { labels: [], values: [] } },
  bonds_info: [],
  bonds_ts: {},
  setores: [],
  pl_total: 0,
  pl_por_carteira: {},
  news_data: { noticias: [], ctx: {}, rf: {}, insight: {}, livro: {}, filme: null, data: '', dia: '', hora: '' },
  alertas: [],
  fatos_relevantes: [],
  bcb_live: {},
  build_info: { gerado_em: '—', modo: 'Aguardando geração', modo_num: '0', dados_vivos: false, arquivos: [] },
  carteiras: [],
  officers: [],
  logo_html: '<div style="font-size:17px;font-weight:700;color:#b69d74;letter-spacing:1px">DOURO CAPITAL</div>',
}

async function getData() {
  // Produção (Vercel): lê do Blob Storage
  const blobUrl = process.env.BLOB_URL
  if (blobUrl) {
    try {
      const res = await fetch(blobUrl, { cache: 'no-store' })
      if (res.ok) return res.json()
    } catch {
      // cai no fallback abaixo
    }
  }
  // Desenvolvimento local: lê do arquivo gerado pelo pipeline Python
  const dataPath = path.join(process.cwd(), 'public', 'data', 'dashboard.json')
  if (!existsSync(dataPath)) return EMPTY_DATA
  try {
    return JSON.parse(readFileSync(dataPath, 'utf-8'))
  } catch {
    return EMPTY_DATA
  }
}

export const dynamic = 'force-dynamic'

export default async function Home() {
  const data = await getData()
  return <DashboardClient data={data} />
}
