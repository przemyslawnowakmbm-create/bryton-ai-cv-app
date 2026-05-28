import { createFileRoute, Link } from '@tanstack/react-router'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useState } from 'react'
import { apiMutate } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'

const forgotPasswordSchema = z.object({
  email: z.string().email('Please enter a valid email address'),
})

type ForgotPasswordForm = z.infer<typeof forgotPasswordSchema>

export const Route = createFileRoute('/forgot-password')({
  component: ForgotPasswordPage,
})

function ForgotPasswordPage() {
  // Always show success to prevent email enumeration (even if email doesn't exist)
  const [submitted, setSubmitted] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ForgotPasswordForm>({
    resolver: zodResolver(forgotPasswordSchema),
  })

  async function onSubmit(data: ForgotPasswordForm) {
    try {
      await apiMutate('/auth/forgot-password', 'POST', { email: data.email })
    } catch {
      // Intentionally silenced — always show success to prevent email enumeration
    }
    setSubmitted(true)
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
          <p className="mt-4 text-sm text-muted-foreground">Reset your password</p>
        </div>

        <Card className="w-full">
          <CardHeader className="pb-4">
            <CardTitle className="text-xl">Forgot password</CardTitle>
            <CardDescription>
              Enter your email and we&apos;ll send you a reset link
            </CardDescription>
          </CardHeader>
          <CardContent>
            {submitted ? (
              <div className="space-y-4">
                <p className="text-sm text-muted-foreground">
                  If an account exists with that email address, we&apos;ve sent a password
                  reset link. Check your inbox and spam folder.
                </p>
                <Link
                  to="/login"
                  className="text-sm text-[hsl(var(--ec-primary))] hover:underline font-medium"
                >
                  Back to sign in
                </Link>
              </div>
            ) : (
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

                {/* Submit */}
                <Button
                  type="submit"
                  disabled={isSubmitting}
                  className="w-full bg-[hsl(var(--ec-primary))] hover:bg-[hsl(var(--ec-primary))]/90 text-white min-h-[44px]"
                >
                  {isSubmitting ? 'Sending...' : 'Send reset link'}
                </Button>

                <p className="text-center text-sm text-muted-foreground">
                  <Link
                    to="/login"
                    className="text-[hsl(var(--ec-primary))] hover:underline font-medium"
                  >
                    Back to sign in
                  </Link>
                </p>
              </form>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
