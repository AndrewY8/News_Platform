/** @type {import('next').NextConfig} */
const nextConfig = {
  eslint: {
    ignoreDuringBuilds: true,
  },
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
  // Enable standalone output for Docker
  output: 'standalone',
  // Remove static export for dynamic website
  // output: 'export',
  // trailingSlash: true,
  // distDir: 'out',
}

export default nextConfig
