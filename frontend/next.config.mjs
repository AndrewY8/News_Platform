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
  // Remove static export for dynamic website
  // output: 'export',
  // trailingSlash: true,
  // distDir: 'out',
}

export default nextConfig
