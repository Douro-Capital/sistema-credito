import { readFile } from 'fs/promises'
import path from 'path'
import DashboardClient, { DashboardData } from '@/components/DashboardClient'

export const dynamic = 'force-dynamic'

export default async function Home() {
  let data: DashboardData

  if (process.env.BLOB_URL) {
    // Produção (Vercel): busca dashboard.json do Vercel Blob
    const res = await fetch(process.env.BLOB_URL, { cache: 'no-store' })
    if (!res.ok) {
      throw new Error(`Falha ao buscar dashboard.json do Blob: ${res.status} ${res.statusText}`)
    }
    data = await res.json()
  } else {
    // Desenvolvimento: lê arquivo local
    const filePath = path.join(process.cwd(), 'public', 'data', 'dashboard.json')
    const raw = await readFile(filePath, 'utf-8')
    data = JSON.parse(raw)
  }

  return <DashboardClient data={data} />
}
