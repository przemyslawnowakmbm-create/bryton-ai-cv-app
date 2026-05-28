import { createFileRoute, Link } from '@tanstack/react-router'
import { useEffect, useState } from 'react'
import { z } from 'zod'
import { apiMutate } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

const verifyEmailSearchSchema = z.object({
  token: z.string().optional(),
})

export const Route = createFileRoute('/verify-email')({
  validateSearch: verifyEmailSearchSchema,
  component: VerifyEmailPage,
})

type VerifyState = 'loading' | 'success' | 'error'

function VerifyEmailPage() {
  const { token } = Route.useSearch()
  const [state, setState] = useState<VerifyState>('loading')

  useEffect(() => {
    if (!token) {
      setState('error')
      return
    }

    let cancelled = false

    apiMutate('/auth/verify-email', 'POST', { token })
      .then(() => {
        if (!cancelled) setState('success')
      })
      .catch(() => {
        if (!cancelled) setState('error')
      })

    return () => {
      cancelled = true
    }
  }, [token])

  return (
    <div className="min-h-dvh flex items-center justify-center bg-background px-4">
      <div className="w-full max-w-md">
        {/* Branding */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-[hsl(var(--ec-primary))] mb-2">
            Bryton AI
          </h1>
          <div className="ec-accent-line mx-auto w-24 mt-2" />
        </div>

        <Card className="w-full">
          <CardHeader className="pb-4">
            <CardTitle className="text-xl">Email verification</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {state === 'loading' && (
              <div className="flex items-center gap-3">
                {/* Accessible spinner */}
                <span
                  className="inline-block h-5 w-5 rounded-full border-2 border-[hsl(var(--ec-primary))] border-t-transparent animate-spin"
                  role="status"
                  aria-label="Verifying your email"
                />
                <p className="text-sm text-muted-foreground">Verifying your email address…</p>
              </div>
            )}

            {state === 'success' && (
              <div className="space-y-3">
                <p className="text-sm text-[hsl(var(--ec-success))] font-medium">
                  Email verified successfully!
                </p>
                <p className="text-sm text-muted-foreground">
                  Your account is now active. You can sign in with your credentials.
                </p>
                <Link
                  to="/login"
                  className="text-sm text-[hsl(var(--ec-primary))] hover:underline font-medium"
                >
                  Go to sign in
                </Link>
              </div>
            )}

            {state === 'error' && (
              <div className="space-y-3">
                <p className="text-sm text-destructive font-medium">
                  Invalid or expired verification link.
                </p>
                <p className="text-sm text-muted-foreground">
                  This link may have expired or already been used. Please register again to
                  receive a new verification email.
                </p>
                <Link
                  to="/register"
                  className="text-sm text-[hsl(var(--ec-primary))] hover:underline font-medium"
                >
                  Register again
                </Link>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
