import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'

export interface User {
  id: string
  email: string
  role: 'admin' | 'sm' | 'recruiter' | 'customer' | 'candidate'
  tenant_id: string | null
  display_name: string | null
}

interface AuthState {
  user: User | null
  accessToken: string | null
  _hasHydrated: boolean
  setAuth: (user: User, accessToken: string) => void
  clearAuth: () => void
  setHasHydrated: (val: boolean) => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      _hasHydrated: false,
      setAuth: (user, accessToken) => set({ user, accessToken }),
      clearAuth: () => set({ user: null, accessToken: null }),
      setHasHydrated: (val) => set({ _hasHydrated: val }),
    }),
    {
      name: 'bryton-auth',
      // sessionStorage: XSS protection — token is lost on tab close, not readable across
      // origins, and not persisted to disk. Per locked decision: NOT localStorage.
      storage: createJSONStorage(() => sessionStorage),
      // Only persist user and accessToken, not the _hasHydrated flag
      partialize: (state) => ({
        user: state.user,
        accessToken: state.accessToken,
      }),
      onRehydrateStorage: () => (state) => {
        // Called when rehydration completes (or fails). Sets _hasHydrated so that
        // TanStack Router's beforeLoad can safely read auth state on hard refresh.
        if (state) {
          state.setHasHydrated(true)
        }
      },
    }
  )
)

/**
 * Returns a Promise that resolves when the Zustand persist store has finished
 * rehydrating from sessionStorage. This is required by TanStack Router's beforeLoad:
 * without waiting for hydration, a hard refresh would redirect to /login even if
 * the user has a valid token in sessionStorage.
 */
export function waitForHydration(): Promise<void> {
  return new Promise((resolve) => {
    const state = useAuthStore.getState()
    if (state._hasHydrated) {
      resolve()
      return
    }
    const unsubscribe = useAuthStore.subscribe((s) => {
      if (s._hasHydrated) {
        unsubscribe()
        resolve()
      }
    })
  })
}
