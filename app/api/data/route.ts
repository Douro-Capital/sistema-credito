import { NextResponse } from 'next/server'
import { readFileSync, existsSync } from 'fs'
import path from 'path'

export const dynamic = 'force-dynamic'

export async function GET() {
  // Produção (Vercel): serve do Blob Storage
  const blobUrl = process.env.BLOB_URL
  if (blobUrl) {
    try {
      const res = await fetch(blobUrl, { cache: 'no-store' })
      if (res.ok) {
        const data = await res.json()
        return NextResponse.json(data, { headers: { 'Cache-Control': 'no-store' } })
      }
    } catch (e) {
      console.error('[/api/data] Blob fetch falhou:', e)
    }
  }
  // Desenvolvimento local: serve do arquivo gerado pelo pipeline Python
  const dataPath = path.join(process.cwd(), 'public', 'data', 'dashboard.json')
  if (!existsSync(dataPath)) {
    return NextResponse.json(
      { error: 'Dados não encontrados. Execute "Oveview Crédito.py" e depois "upload_dashboard.py".' },
      { status: 404 }
    )
  }
  try {
    const data = JSON.parse(readFileSync(dataPath, 'utf-8'))
    return NextResponse.json(data, { headers: { 'Cache-Control': 'no-store' } })
  } catch (e) {
    console.error('[/api/data] Leitura local falhou:', e)
    return NextResponse.json({ error: 'Erro ao ler dados.' }, { status: 500 })
  }
}
