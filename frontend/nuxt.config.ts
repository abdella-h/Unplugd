// https://nuxt.com/docs/api/configuration/nuxt-config
// Same-origin proxy to the three backend services (ADR-0004 keeps the
// refresh cookie SameSite=Strict, so the frontend must be same-site with
// the APIs). Targets are baked in at build time: plain `npm run build`
// defaults to host-local ports, while the container image sets the
// NUXT_*_API_URL vars to the compose service names (see frontend/dockerfile).
const authApi = process.env.NUXT_AUTH_API_URL ?? 'http://localhost:8000'
const devicesApi =
  process.env.NUXT_DEVICES_API_URL ?? 'http://localhost:8004'
const dashboardApi =
  process.env.NUXT_DASHBOARD_API_URL ?? 'http://localhost:8002'

export default defineNuxtConfig({
  modules: ['@nuxt/ui'],
  css: ['~/assets/css/main.css'],
  colorMode: {
    preference: 'dark',
    fallback: 'dark',
  },
  app: {
    head: {
      title: 'Unplugd',
      titleTemplate: '%s · Unplugd',
      htmlAttrs: { lang: 'en' },
      meta: [
        {
          name: 'description',
          content: 'Human-reported datacenter monitoring for calm, accountable operations.',
        },
        { name: 'theme-color', content: '#080D16' },
      ],
      link: [{ rel: 'icon', type: 'image/svg+xml', href: '/favicon.svg' }],
    },
  },
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
