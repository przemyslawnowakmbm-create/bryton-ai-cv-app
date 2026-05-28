import { StrictMode, useEffect } from 'react'
import ReactDOM from 'react-dom/client'
import { RouterProvider, createRouter } from '@tanstack/react-router'
import { routeTree } from './routeTree.gen'
import { useAuthStore, waitForHydration } from './stores/auth'
import { type RouterContext } from './routes/__root'

// Build initial auth context from store state.
// sessionStorage is synchronous — Zustand persist reads it immediately.
// waitForHydration() handles the edge case where onRehydrateStorage fires async.
function getAuthContext(): RouterContext['auth'] {
  const { user, accessToken } = useAuthStore.getState()
  return {
    isAuthenticated: !!accessToken,
    user,
    role: user?.role ?? null,
  }
}

const router = createRouter({
  routeTree,
  context: {
    auth: getAuthContext(),
  },
})

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}

/**
 * App component subscribes to auth state changes and invalidates the router
 * so that beforeLoad guards re-evaluate when the user logs in or out.
 */
function App() {
  const { user, accessToken } = useAuthStore()

  useEffect(() => {
    router.invalidate()
  }, [user, accessToken])

  return (
    <RouterProvider
      router={router}
      context={{
        auth: {
          isAuthenticated: !!accessToken,
          user,
          role: user?.role ?? null,
        },
      }}
    />
  )
}

// Wait for Zustand to rehydrate from sessionStorage before mounting.
// This ensures that on a hard refresh, beforeLoad guards see the correct
// auth state instead of briefly redirecting to /login.
waitForHydration().then(() => {
  ReactDOM.createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <App />
    </StrictMode>
  )
})
