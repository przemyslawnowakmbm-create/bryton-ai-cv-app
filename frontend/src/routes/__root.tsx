import { createRootRoute, Outlet } from '@tanstack/react-router'
import '../index.css'

export const Route = createRootRoute({
  component: () => (
    <div className="min-h-screen bg-background font-sans antialiased">
      <Outlet />
    </div>
  ),
})
