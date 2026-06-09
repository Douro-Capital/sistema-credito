import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Douro Capital — Overview Crédito',
  description: 'Dashboard de crédito privado Douro Capital',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <head />
      <body style={{ margin: 0, padding: 0, overflow: 'hidden', background: '#0d1520' }}>
        {children}
      </body>
    </html>
  )
}
