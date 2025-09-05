import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'PathFinder',
  description: 'AI-powered GE Lab chatbot for business insights',
  generator: 'PathFinder',
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
