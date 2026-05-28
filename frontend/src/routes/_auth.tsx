import {
  createFileRoute,
  Outlet,
  Link,
  useRouterState,
  redirect,
  useNavigate,
} from '@tanstack/react-router'
import { useAuthStore } from '@/stores/auth'
import { apiFetch } from '@/lib/api'

export const Route = createFileRoute('/_auth')({
  beforeLoad: ({ context, location }) => {
    if (!context.auth.isAuthenticated) {
      throw redirect({
        to: '/login',
        search: { redirect: location.href },
      })
    }
  },
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

// Role badge styles per role
const roleBadgeClass: Record<string, string> = {
  admin: 'bg-purple-100 text-purple-800',
  sm: 'bg-blue-100 text-blue-800',
  recruiter: 'bg-green-100 text-green-800',
  customer: 'bg-amber-100 text-amber-800',
  candidate: 'bg-slate-100 text-slate-800',
}

function AuthLayout() {
  const routerState = useRouterState()
  const currentPath = routerState.location.pathname
  const navigate = useNavigate()
  const user = useAuthStore((s) => s.user)
  const clearAuth = useAuthStore((s) => s.clearAuth)

  async function handleLogout() {
    try {
      // Invalidate the refresh token server-side
      await apiFetch('/auth/logout', { method: 'POST' })
    } catch {
      // If the request fails (e.g. network error), still clear client state
    }
    clearAuth()
    navigate({ to: '/login' })
  }

  const roleLabel = user?.role ?? ''
  const badgeClass = roleBadgeClass[roleLabel] ?? 'bg-slate-100 text-slate-800'

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
            const isActive =
              currentPath === item.to || currentPath.startsWith(item.to + '/')
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

        {/* Footer — user info + logout */}
        <div className="px-4 py-4 border-t border-white/10 space-y-3">
          {user && (
            <div className="space-y-1">
              <p className="text-xs text-blue-200 truncate" title={user.email}>
                {user.display_name ?? user.email}
              </p>
              <p className="text-xs text-blue-300 truncate">{user.email}</p>
              <span
                className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${badgeClass}`}
              >
                {roleLabel}
              </span>
            </div>
          )}
          <button
            onClick={handleLogout}
            className="w-full text-left px-3 py-2 rounded-md text-sm font-medium text-blue-200 hover:text-white hover:bg-white/10 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/50"
            aria-label="Sign out of Bryton AI"
          >
            Sign out
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto bg-background">
        <Outlet />
      </main>
    </div>
  )
}
