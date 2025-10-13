/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  // Type checking and linting are now enabled - all errors fixed!
  eslint: {
    ignoreDuringBuilds: false,
  },
  typescript: {
    ignoreBuildErrors: false,
  },
  images: {
    unoptimized: true,
  },
}

export default nextConfig
