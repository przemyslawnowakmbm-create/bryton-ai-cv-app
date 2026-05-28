---
phase: 02-auth-tenancy-rbac
plan: "03"
subsystem: frontend-auth
tags: [zustand, tanstack-router, react-hook-form, zod, auth-pages, api-client]
dependency_graph:
  requires: [02-01]
  provides: [frontend-auth-store, api-client, auth-guard, auth-pages]
  affects: [all-frontend-routes]
tech_stack:
  added:
    - "@hookform/resolvers ^3.x — Zod resolver bridge for react-hook-form"
  patterns:
    - "Zustand persist (sessionStorage) with _hasHydrated flag + waitForHydration()"
    - "Single-flight 401 refresh with promise queue"
    - "createRootRouteWithContext for threading auth into router"
    - "beforeLoad guard on _auth layout for route protection"
    - "react-hook-form + Zod for form validation"
key_files:
  created:
    - frontend/src/stores/auth.ts
    - frontend/src/lib/api.ts
    - frontend/src/routes/register.tsx
    - frontend/src/routes/register.candidate.tsx
    - frontend/src/routes/verify-email.tsx
    - frontend/src/routes/forgot-password.tsx
    - frontend/src/routes/reset-password.tsx
  modified:
    - frontend/src/routes/__root.tsx
    - frontend/src/routes/_auth.tsx
    - frontend/src/routes/login.tsx
    - frontend/src/main.tsx
    - frontend/package.json
decisions:
  - "sessionStorage (not localStorage) for access token — XSS protection; token lost on tab close is acceptable tradeoff"
  - "waitForHydration() called before ReactDOM.createRoot to prevent hard-refresh redirect loop"
  - "Single-flight refresh with promise queue prevents concurrent 401s from each triggering a separate /auth/refresh call"
  - "router.invalidate() called on auth state changes to force beforeLoad re-evaluation"
  - "GDPR consent uses z.literal(true) — Zod guarantees checkbox must be checked, not just truthy"
  - "Forgot-password always shows success message to prevent email enumeration"
metrics:
  duration: "~25 minutes"
  completed: "2026-05-28T14:38:41Z"
  tasks_completed: 3
  tasks_total: 3
  files_created: 7
  files_modified: 4
---

# Phase 2 Plan 03: Frontend Auth Experience Summary

Zustand auth store with sessionStorage persist, API client with single-flight 401 refresh, TanStack Router auth guard, and 6 auth pages (login, register, candidate register, email verify, forgot/reset password) using the EUROCONTROL design system.

## What Was Built

### Task 1: Zustand Auth Store and API Client (commit d89e7d2)

**`frontend/src/stores/auth.ts`** — Auth state with persist middleware:
- `useAuthStore` with `user`, `accessToken`, `_hasHydrated` state
- `persist` using `createJSONStorage(() => sessionStorage)` — NOT localStorage (XSS protection, locked decision)
- `partialize` excludes `_hasHydrated` from persisted state (only user + accessToken persisted)
- `onRehydrateStorage` callback sets `_hasHydrated: true` when hydration completes
- `waitForHydration()` exported — returns a Promise that resolves when `_hasHydrated` is true, using Zustand `subscribe`

**`frontend/src/lib/api.ts`** — API fetch wrapper:
- `apiFetch<T>` sends `Authorization: Bearer {token}` + `credentials: 'include'` on every request
- On 401: single-flight refresh with module-level `isRefreshing` flag and `refreshQueue` array
  - If `isRefreshing` is already true, queues the retry; all queued retries resolve/reject when the single refresh completes
  - If refresh succeeds (200): calls `setAuth`, processes queue with new token, retries original request once
  - If refresh fails: processes queue with null, calls `clearAuth()`, redirects to `/login`
- `apiMutate<T>` convenience wrapper for mutations with JSON body

### Task 2: TanStack Router Auth Guards (commit d646e35)

**`frontend/src/routes/__root.tsx`** — Changed from `createRootRoute` to `createRootRouteWithContext<RouterContext>()`:
- `RouterContext` interface: `{ auth: { isAuthenticated: boolean; user: User | null; role: string | null } }`
- Fixed `min-h-screen` to `min-h-dvh` (mobile browser chrome support)

**`frontend/src/main.tsx`** — Updated to pass context + subscribe to auth changes:
- `waitForHydration()` called before `ReactDOM.createRoot` — prevents hard-refresh redirect loop
- `App` component subscribes to `useAuthStore` and calls `router.invalidate()` on `user`/`accessToken` changes
- `RouterProvider` receives dynamic `context` prop reflecting current auth state

**`frontend/src/routes/_auth.tsx`** — Added `beforeLoad` guard:
- Redirects to `/login?redirect={current-href}` when `!context.auth.isAuthenticated`
- Sidebar footer shows: display_name or email, email (second line), role badge with per-role colors
- Logout handler: `POST /auth/logout` (server-side token invalidation), then `clearAuth()` + navigate to `/login`

### Task 3: Auth Pages (commit e40e964)

All pages share: `min-h-dvh` container, centered Card, Bryton AI branding + EC accent line, EC design system colors, Exo font, accessible labels/inputs.

| Page | Route | Key Behavior |
|------|-------|-------------|
| **login.tsx** | `/login` | Email + password form; maps 401/403/429 to user-friendly messages; redirects to `?redirect` or `/dashboard` on success |
| **register.tsx** | `/register` | Display name (optional), email, password, confirm; shows "check your email" success state |
| **register.candidate.tsx** | `/register/candidate` | Same as register + GDPR consent checkbox (`z.literal(true)`) |
| **verify-email.tsx** | `/verify-email?token=` | Auto-verifies on mount; loading spinner → success/error state |
| **forgot-password.tsx** | `/forgot-password` | Silences all errors; always shows success message (anti-enumeration) |
| **reset-password.tsx** | `/reset-password?token=` | Password + confirm; transitions to success or error state |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Missing Dependency] Installed @hookform/resolvers**
- **Found during:** Task 3 planning — react-hook-form requires this bridge package for Zod resolvers
- **Issue:** `@hookform/resolvers` not in package.json but required for `zodResolver(schema)` integration
- **Fix:** `npm install @hookform/resolvers` — adds the bridge between react-hook-form and Zod
- **Files modified:** `frontend/package.json`, `frontend/package-lock.json`
- **Commit:** d89e7d2

**2. [Rule 3b - A11y/UX] min-h-screen to min-h-dvh**
- **Found during:** Task 2 (root layout) and Task 3 (all auth pages)
- **Issue:** `min-h-screen` does not account for mobile browser chrome (address bar)
- **Fix:** Replaced with `min-h-dvh` in `__root.tsx` and all auth page containers
- **Files modified:** `__root.tsx`, all auth page files
- **Commits:** d646e35, e40e964

## Verification Results

All plan verification checks passed:

1. `npx tsc --noEmit` — zero TypeScript errors
2. `grep sessionStorage frontend/src/stores/auth.ts` — confirmed sessionStorage (line 35)
3. `grep "credentials.*include" frontend/src/lib/api.ts` — confirmed at lines 35, 50, 68, 80
4. `grep "beforeLoad" frontend/src/routes/_auth.tsx` — confirmed at line 13
5. All 6 route files exist and export `Route` objects via `createFileRoute`

## Self-Check: PASSED

Files created:
- `frontend/src/stores/auth.ts` — FOUND
- `frontend/src/lib/api.ts` — FOUND
- `frontend/src/routes/register.tsx` — FOUND
- `frontend/src/routes/register.candidate.tsx` — FOUND
- `frontend/src/routes/verify-email.tsx` — FOUND
- `frontend/src/routes/forgot-password.tsx` — FOUND
- `frontend/src/routes/reset-password.tsx` — FOUND

Commits exist:
- d89e7d2 — FOUND (feat(02-03): Zustand auth store and API client with 401 refresh)
- d646e35 — FOUND (feat(02-03): TanStack Router auth guards and root context)
- e40e964 — FOUND (feat(02-03): auth pages with EUROCONTROL design system)
