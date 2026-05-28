import { createRootRouteWithContext, Outlet } from '@tanstack/react-router'
import { type User } from '@/stores/auth'
import '../index.css'

export interface RouterContext {
  auth: {
    isAuthenticated: boolean
    user: User | null
    role: string | null
  }
}

export const Route = createRootRouteWithContext<RouterContext>()({
  component: () => (
    <div className="min-h-dvh bg-background font-sans antialiased">
      <Outlet />
    </div>
  ),
})
