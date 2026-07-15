import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'CampusAgent',
  description: 'Privacy-first, agent-native campus communication platform',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="zh-CN">
      <body>
        {children}
      </body>
    </html>
  )
}
