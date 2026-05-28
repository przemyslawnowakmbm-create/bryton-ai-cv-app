import { useAuthStore } from '@/stores/auth'

const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

// Single-flight refresh: prevents multiple concurrent 401s from each triggering
// a separate /auth/refresh call. All queued requests wait for the single refresh
// promise to resolve, then retry.
let isRefreshing = false
let refreshQueue: Array<(token: string | null) => void> = []

function processQueue(token: string | null): void {
  refreshQueue.forEach((callback) => callback(token))
  refreshQueue = []
}

/**
 * Core API fetch wrapper.
 * - Sends Authorization: Bearer {token} header when authenticated
 * - Sends credentials: 'include' so the httpOnly refresh_token cookie is included
 * - On 401: attempts a single token refresh (with single-flight dedup)
 *   - If refresh succeeds: retries the original request once
 *   - If refresh fails: clears auth state and redirects to /login
 */
export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const { accessToken } = useAuthStore.getState()

  const buildHeaders = (token: string | null): HeadersInit => ({
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...init?.headers,
  })

  const res = await fetch(`${BASE}${path}`, {
    ...init,
    credentials: 'include',
    headers: buildHeaders(accessToken),
  })

  if (res.status === 401) {
    // Already refreshing: queue this retry
    if (isRefreshing) {
      return new Promise<T>((resolve, reject) => {
        refreshQueue.push((newToken) => {
          if (newToken === null) {
            reject(new Error('Session expired'))
            return
          }
          fetch(`${BASE}${path}`, {
            ...init,
            credentials: 'include',
            headers: buildHeaders(newToken),
          })
            .then((r) => {
              if (!r.ok) return r.text().then((t) => Promise.reject(new Error(t)))
              return r.json() as Promise<T>
            })
            .then(resolve)
            .catch(reject)
        })
      })
    }

    isRefreshing = true

    try {
      const refreshRes = await fetch(`${BASE}/auth/refresh`, {
        method: 'POST',
        credentials: 'include',
      })

      if (refreshRes.ok) {
        const data = (await refreshRes.json()) as { user: Parameters<typeof useAuthStore.getState['setAuth']>[0]; access_token: string }
        useAuthStore.getState().setAuth(data.user, data.access_token)
        processQueue(data.access_token)
        isRefreshing = false

        // Retry original request with new token
        const retry = await fetch(`${BASE}${path}`, {
          ...init,
          credentials: 'include',
          headers: buildHeaders(data.access_token),
        })
        if (!retry.ok) throw new Error(await retry.text())
        return retry.json() as Promise<T>
      } else {
        // Refresh failed: clear auth and redirect
        processQueue(null)
        isRefreshing = false
        useAuthStore.getState().clearAuth()
        window.location.href = '/login'
        throw new Error('Session expired')
      }
    } catch (err) {
      processQueue(null)
      isRefreshing = false
      useAuthStore.getState().clearAuth()
      window.location.href = '/login'
      throw err
    }
  }

  if (!res.ok) {
    throw new Error(await res.text())
  }

  return res.json() as Promise<T>
}

/**
 * Convenience wrapper for mutations (POST, PUT, PATCH, DELETE) with a JSON body.
 */
export async function apiMutate<T>(
  path: string,
  method: string,
  body?: unknown
): Promise<T> {
  return apiFetch<T>(path, {
    method,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
}
