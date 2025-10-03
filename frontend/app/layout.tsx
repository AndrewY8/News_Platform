import type { Metadata } from 'next'
import { GeistSans } from 'geist/font/sans'
import { GeistMono } from 'geist/font/mono'
import { Karma } from 'next/font/google'
import './globals.css'

const karma = Karma({ 
  subsets: ['latin'],
  weight: ['300', '400', '500', '600', '700']
})

export const metadata: Metadata = {
  title: 'Haven News',
  description: 'AI-powered financial news personalization',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className={`${GeistSans.variable} ${GeistMono.variable} ${karma.className}`}>
      <body className={`${karma.className} antialiased`}>
        {children}
      </body>
    </html>
  )
}