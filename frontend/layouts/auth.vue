<template>
  <div class="min-h-screen bg-[var(--monitor-canvas)] text-[var(--monitor-text)] lg:grid lg:grid-cols-[minmax(360px,0.9fr)_minmax(520px,1.1fr)]">
    <section class="relative hidden overflow-hidden bg-slate-950 p-10 text-white lg:flex lg:flex-col lg:justify-between xl:p-14">
      <div class="absolute inset-0 opacity-30" aria-hidden="true">
        <div class="absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(34,211,238,0.28),transparent_34%),radial-gradient(circle_at_80%_70%,rgba(14,116,144,0.24),transparent_38%)]" />
        <div class="absolute inset-0 bg-[linear-gradient(rgba(148,163,184,0.08)_1px,transparent_1px),linear-gradient(90deg,rgba(148,163,184,0.08)_1px,transparent_1px)] bg-[size:48px_48px]" />
      </div>
      <div class="relative">
        <BrandLogo class="text-white" />
      </div>
      <div class="relative max-w-xl">
        <p class="text-xs font-semibold uppercase tracking-[0.22em] text-cyan-300">
          Human-reported infrastructure visibility
        </p>
        <h1 class="mt-5 text-4xl font-semibold leading-tight tracking-tight xl:text-5xl">
          Know what needs attention across every Datacenter.
        </h1>
        <p class="mt-5 max-w-lg text-base leading-7 text-slate-300">
          One calm operational view for Device State, Open Alerts, and accountable Acknowledgment.
        </p>
      </div>
      <div class="relative flex items-center gap-6 text-xs text-slate-400">
        <span class="flex items-center gap-2"><span class="h-2 w-2 rounded-full bg-emerald-400" />Operational context</span>
        <span class="flex items-center gap-2"><span class="h-2 w-2 rounded-full bg-amber-400" />Human observation</span>
        <span class="flex items-center gap-2"><span class="h-2 w-2 rounded-full bg-red-400" />Actionable State</span>
      </div>
    </section>
    <main class="flex min-h-screen items-center justify-center px-4 py-10 sm:px-8 lg:px-12">
      <div class="w-full max-w-md">
        <BrandLogo class="mb-10 lg:hidden" />
        <slot />
      </div>
    </main>
  </div>
</template>
