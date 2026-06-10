import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Douro Capital — Overview Crédito',
  description: 'Dashboard de crédito privado Douro Capital',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="pt-BR" suppressHydrationWarning>
      <body style={{ margin: 0, padding: 0 }}>
        {children}
      </body>
    </html>
  )
}
