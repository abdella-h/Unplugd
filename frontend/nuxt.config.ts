// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  modules: ['@nuxt/ui'],
  // SPA mode: access tokens live in memory and the refresh cookie is
  // HttpOnly, so there is nothing useful to render server-side.
  ssr: false,
  devtools: { enabled: false },
  // Same-origin proxy to the three backend services (ADR-0004 keeps the
  // refresh cookie SameSite=Strict, so the frontend must be same-site with
  // the APIs). In production, a reverse proxy must replicate these routes.
  routeRules: {
    '/api/auth/**': { proxy: 'http://localhost:8000/**' },
    '/api/devices/**': { proxy: 'http://localhost:8001/**' },
    '/api/dashboard/**': { proxy: 'http://localhost:8002/**' },
  },
  compatibilityDate: '2024-11-01',
})
