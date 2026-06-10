import { NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

export async function GET() {
  const blobHtmlUrl = process.env.BLOB_HTML_URL

  if (blobHtmlUrl) {
    try {
      const res = await fetch(blobHtmlUrl, { cache: 'no-store' })
      if (res.ok) {
        const html = await res.text()
        return new NextResponse(html, {
          headers: {
            'Content-Type': 'text/html; charset=utf-8',
            'Cache-Control': 'no-store',
          },
        })
      }
    } catch (e) {
      console.error('[/api/dashboard] Blob fetch falhou:', e)
    }
  }

  // Fallback local
  const { readFileSync, existsSync } = await import('fs')
  const path = await import('path')
  const localPath = path.join(process.cwd(), 'public', 'dashboard.html')

  if (existsSync(localPath)) {
    const html = readFileSync(localPath, 'utf-8')
    return new NextResponse(html, {
      headers: { 'Content-Type': 'text/html; charset=utf-8' },
    })
  }

  return new NextResponse('Dashboard não encontrado', { status: 404 })
}
