export default defineAppConfig({
  ui: {
    primary: 'cyan',
    gray: 'slate',
    button: {
      rounded: 'rounded-md',
      variant: {
        solid:
          'bg-primary-700 text-white hover:bg-primary-800 dark:bg-primary-300 dark:text-slate-950 dark:hover:bg-primary-200 focus-visible:ring-2 focus-visible:ring-primary-700 dark:focus-visible:ring-primary-300',
        soft:
          'bg-{color}-100 text-{color}-800 hover:bg-{color}-200 dark:bg-{color}-950 dark:bg-opacity-40 dark:text-{color}-200 dark:hover:bg-opacity-60',
        outline:
          'text-{color}-800 ring-1 ring-inset ring-{color}-400 hover:bg-{color}-100 dark:text-{color}-200 dark:ring-{color}-600 dark:hover:bg-{color}-950 dark:hover:bg-opacity-40',
        ghost:
          'text-{color}-800 hover:bg-{color}-100 dark:text-{color}-200 dark:hover:bg-{color}-950 dark:hover:bg-opacity-40',
        link:
          'text-{color}-800 hover:text-{color}-900 dark:text-{color}-200 dark:hover:text-{color}-100',
      },
    },
    badge: {
      variant: {
        subtle:
          'bg-{color}-100 dark:bg-{color}-950 dark:bg-opacity-40 text-{color}-800 dark:text-{color}-200 ring-1 ring-inset ring-{color}-300 dark:ring-{color}-700 ring-opacity-50 dark:ring-opacity-40',
      },
    },
    alert: {
      variant: {
        soft:
          'bg-{color}-100 dark:bg-{color}-950 dark:bg-opacity-40 text-{color}-800 dark:text-{color}-200',
        subtle:
          'bg-{color}-100 dark:bg-{color}-950 dark:bg-opacity-40 text-{color}-800 dark:text-{color}-200 ring-1 ring-inset ring-{color}-300 dark:ring-{color}-700 ring-opacity-50 dark:ring-opacity-40',
      },
    },
    card: {
      background: 'bg-white dark:bg-[#101827]',
      ring: 'ring-1 ring-[#D7DFEA] dark:ring-[#28364C]',
      rounded: 'rounded-lg',
      shadow: 'shadow-none',
      body: {
        padding: 'px-5 py-4',
      },
      header: {
        padding: 'px-5 py-4',
      },
      footer: {
        padding: 'px-5 py-4',
      },
    },
    input: {
      rounded: 'rounded-md',
      color: {
        white: {
          outline:
            'bg-white dark:bg-[#101827] text-gray-900 dark:text-gray-100 ring-1 ring-inset ring-[#D7DFEA] dark:ring-[#28364C] focus:ring-2 focus:ring-primary-700 dark:focus:ring-primary-300',
        },
      },
    },
    table: {
      divide: 'divide-y divide-[#D7DFEA] dark:divide-[#28364C]',
      tbody: 'divide-y divide-[#E5EAF0] dark:divide-[#202C3F]',
      th: {
        padding: 'px-3 py-2.5',
        color: 'text-gray-600 dark:text-gray-300',
        size: 'text-xs',
      },
      td: {
        padding: 'px-3 py-3',
        color: 'text-gray-700 dark:text-gray-200',
        size: 'text-xs',
      },
      tr: {
        active: 'hover:bg-gray-50 dark:hover:bg-[#172033]',
      },
    },
    modal: {
      background: 'bg-white dark:bg-[#101827]',
      rounded: 'rounded-xl',
      overlay: {
        background: 'bg-slate-950/70 backdrop-blur-sm',
        transition: {
          enter: 'ease-out duration-200',
          enterFrom: 'opacity-0',
          enterTo: 'opacity-100',
          leave: 'ease-in duration-150',
          leaveFrom: 'opacity-100',
          leaveTo: 'opacity-0',
        },
      },
      transition: {
        enter: 'ease-out duration-200',
        enterFrom: 'opacity-0 translate-y-3 sm:translate-y-0 sm:scale-[0.98]',
        enterTo: 'opacity-100 translate-y-0 sm:scale-100',
        leave: 'ease-in duration-150',
        leaveFrom: 'opacity-100 translate-y-0 sm:scale-100',
        leaveTo: 'opacity-0 translate-y-3 sm:translate-y-0 sm:scale-[0.98]',
      },
    },
  },
})
