/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Keep production builds away from the live development cache. Running
  // `next build` while `next dev` is open must not replace its CSS assets.
  distDir: process.env.NEXT_DIST_DIR
    || (process.env.NODE_ENV === 'production' ? '.next-build' : '.next'),
  // 基础配置，不涉及任何UI相关选项
}

module.exports = nextConfig
