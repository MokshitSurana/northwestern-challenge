/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "export",          // static export — no server needed
  trailingSlash: true,
  images: { unoptimized: true },
}

module.exports = nextConfig
