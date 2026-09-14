// https://nuxt.com/docs/api/configuration/nuxt-config
// Same-origin proxy to the three backend services (ADR-0004 keeps the
// refresh cookie SameSite=Strict, so the frontend must be same-site with
// the APIs). Targets are baked in at build time: plain `npm run build`
// defaults to host-local ports, while the container image sets the
// NUXT_*_API_URL vars to the compose service names (see frontend/dockerfile).
const authApi = process.env.NUXT_AUTH_API_URL ?? 'http://localhost:8000'
const devicesApi =
  process.env.NUXT_DEVICES_API_URL ?? 'http://localhost:8001'
const dashboardApi =
  process.env.NUXT_DASHBOARD_API_URL ?? 'http://localhost:8002'

export default defineNuxtConfig({
  modules: ['@nuxt/ui'],
  // SPA mode: access tokens live in memory and the refresh cookie is
  // HttpOnly, so there is nothing useful to render server-side.
  ssr: false,
  devtools: { enabled: false },
  routeRules: {
    '/api/auth/**': { proxy: `${authApi}/**` },
    '/api/devices/**': { proxy: `${devicesApi}/**` },
    '/api/dashboard/**': { proxy: `${dashboardApi}/**` },
  },
  compatibilityDate: '2024-11-01',
})
