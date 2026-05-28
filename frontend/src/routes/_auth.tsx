import { createFileRoute, Outlet, Link, useRouterState } from '@tanstack/react-router'

export const Route = createFileRoute('/_auth')({
  component: AuthLayout,
})

const navItems = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/demands', label: 'Demands' },
  { to: '/candidates', label: 'Candidates' },
  { to: '/contracts', label: 'Contracts' },
  { to: '/profiles', label: 'Profile Catalogue' },
  { to: '/approvals', label: 'Approvals' },
  { to: '/sla', label: 'SLA Dashboard' },
  { to: '/admin', label: 'Admin' },
]

function AuthLayout() {
  const routerState = useRouterState()
  const currentPath = routerState.location.pathname

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside className="w-64 flex-shrink-0 ec-header-gradient flex flex-col">
        {/* Logo area */}
        <div className="px-6 py-5 border-b border-white/10">
          <span className="text-xl font-bold text-white">Bryton AI</span>
          <div className="ec-accent-line mt-1 w-16" />
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const isActive = currentPath === item.to || currentPath.startsWith(item.to + '/')
            return (
              <Link
                key={item.to}
                to={item.to}
                className={`flex items-center px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  isActive
                    ? 'ec-nav-active'
                    : 'text-blue-200 hover:text-white hover:bg-white/10'
                }`}
              >
                {item.label}
              </Link>
            )
          })}
        </nav>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-white/10">
          <p className="text-xs text-blue-300">Phase 1 Scaffold</p>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto bg-background">
        <Outlet />
      </main>
    </div>
  )
}
