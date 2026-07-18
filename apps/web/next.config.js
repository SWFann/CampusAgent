/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  distDir: process.env.NEXT_DIST_DIR || '.next',
  // 基础配置，不涉及任何UI相关选项
}

module.exports = nextConfig
