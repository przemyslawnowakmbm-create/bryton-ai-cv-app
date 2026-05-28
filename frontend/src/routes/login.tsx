import { createFileRoute, Link, useNavigate, useSearch } from '@tanstack/react-router'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useState } from 'react'
import { apiMutate } from '@/lib/api'
import { useAuthStore, type User } from '@/stores/auth'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'

const loginSchema = z.object({
  email: z.string().email('Please enter a valid email address'),
  password: z.string().min(1, 'Password is required'),
})

type LoginForm = z.infer<typeof loginSchema>

interface LoginResponse {
  user: User
  access_token: string
}

// Define the search params shape for the /login route
const loginSearchSchema = z.object({
  redirect: z.string().optional(),
})

export const Route = createFileRoute('/login')({
  validateSearch: loginSearchSchema,
  component: LoginPage,
})

function LoginPage() {
  const navigate = useNavigate()
  const search = useSearch({ from: '/login' })
  const setAuth = useAuthStore((s) => s.setAuth)
  const [serverError, setServerError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
  })

  async function onSubmit(data: LoginForm) {
    setServerError(null)
    try {
      const result = await apiMutate<LoginResponse>('/auth/login', 'POST', {
        email: data.email,
        password: data.password,
      })
      setAuth(result.user, result.access_token)
      // Navigate to redirect param or default dashboard
      const redirectTo = search.redirect ?? '/dashboard'
      navigate({ to: redirectTo as '/' })
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      // Parse HTTP status from error message or body
      if (msg.includes('401') || msg.toLowerCase().includes('invalid')) {
        setServerError('Invalid email or password.')
      } else if (msg.includes('403') || msg.toLowerCase().includes('verify')) {
        setServerError('Please verify your email before signing in.')
      } else if (msg.includes('429') || msg.toLowerCase().includes('many')) {
        setServerError('Too many attempts. Please wait a moment and try again.')
      } else {
        setServerError('Something went wrong. Please try again.')
      }
    }
  }

  return (
    <div className="min-h-dvh flex items-center justify-center bg-background px-4">
      <div className="w-full max-w-md">
        {/* Branding */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-[hsl(var(--ec-primary))] mb-2">
            Bryton AI
          </h1>
          <div className="ec-accent-line mx-auto w-24 mt-2" />
          <p className="mt-4 text-sm text-muted-foreground">
            Sign in to your account
          </p>
        </div>

        <Card className="w-full">
          <CardHeader className="pb-4">
            <CardTitle className="text-xl">Sign in</CardTitle>
            <CardDescription>
              Enter your credentials to access the platform
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
              {/* Email */}
              <div className="space-y-1.5">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  autoComplete="email"
                  placeholder="you@example.com"
                  {...register('email')}
                  aria-invalid={!!errors.email}
                />
                {errors.email && (
                  <p className="text-destructive text-sm">{errors.email.message}</p>
                )}
              </div>

              {/* Password */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <Label htmlFor="password">Password</Label>
                  <Link
                    to="/forgot-password"
                    className="text-sm text-[hsl(var(--ec-primary))] hover:underline"
                  >
                    Forgot password?
                  </Link>
                </div>
                <Input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  placeholder="••••••••"
                  {...register('password')}
                  aria-invalid={!!errors.password}
                />
                {errors.password && (
                  <p className="text-destructive text-sm">{errors.password.message}</p>
                )}
              </div>

              {/* Server error */}
              {serverError && (
                <p className="text-destructive text-sm" role="alert">
                  {serverError}
                </p>
              )}

              {/* Submit */}
              <Button
                type="submit"
                disabled={isSubmitting}
                className="w-full bg-[hsl(var(--ec-primary))] hover:bg-[hsl(var(--ec-primary))]/90 text-white min-h-[44px]"
              >
                {isSubmitting ? 'Signing in...' : 'Sign in'}
              </Button>
            </form>

            <p className="mt-4 text-center text-sm text-muted-foreground">
              Don&apos;t have an account?{' '}
              <Link
                to="/register"
                className="text-[hsl(var(--ec-primary))] hover:underline font-medium"
              >
                Register
              </Link>
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
