/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  
  // Configure API proxy to FastAPI backend
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/:path*',
      },
    ];
  },
  
  // Enable standalone output for production
  output: 'standalone',
  
  // Configure image domains if needed
  images: {
    domains: [],
  },
  
  // Environment variables
  env: {
    CUSTOM_KEY: process.env.CUSTOM_KEY,
  },
  
  // Webpack configuration
  webpack: (config, { buildId, dev, isServer, defaultLoaders, webpack }) => {
    // Custom webpack config if needed
    return config;
  },
  
  // Headers configuration
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'X-Frame-Options',
            value: 'DENY',
          },
          {
            key: 'X-XSS-Protection',
            value: '1; mode=block',
          },
        ],
      },
    ];
  },
  
  // Experimental features
  experimental: {
    // Enable if needed
  },
  
  // Configure ESLint
  eslint: {
    // Ignore ESLint during builds (not recommended for production)
    ignoreDuringBuilds: false,
  },
  
  // TypeScript configuration
  typescript: {
    // Ignore TypeScript errors during builds (not recommended for production)
    ignoreBuildErrors: false,
  },
  
  // Configure redirects
  async redirects() {
    return [
      // Add redirects if needed
    ];
  },
  
  // Configure internationalization if needed
  // i18n: {
  //   locales: ['en', 'hi'],
  //   defaultLocale: 'en',
  // },
};

module.exports = nextConfig;
