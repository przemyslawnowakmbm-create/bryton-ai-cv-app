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

const resetPasswordSchema = z
  .object({
    new_password: z.string().min(8, 'Password must be at least 8 characters'),
    confirm_password: z.string().min(1, 'Please confirm your password'),
  })
  .refine((d) => d.new_password === d.confirm_password, {
    message: 'Passwords do not match',
    path: ['confirm_password'],
  })

type ResetPasswordForm = z.infer<typeof resetPasswordSchema>

const resetPasswordSearchSchema = z.object({
  token: z.string().optional(),
})

export const Route = createFileRoute('/reset-password')({
  validateSearch: resetPasswordSearchSchema,
  component: ResetPasswordPage,
})

type ResetState = 'form' | 'success' | 'error'

function ResetPasswordPage() {
  const { token } = Route.useSearch()
  const [state, setState] = useState<ResetState>('form')

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ResetPasswordForm>({
    resolver: zodResolver(resetPasswordSchema),
  })

  async function onSubmit(data: ResetPasswordForm) {
    if (!token) {
      setState('error')
      return
    }
    try {
      await apiMutate('/auth/reset-password', 'POST', {
        token,
        new_password: data.new_password,
      })
      setState('success')
    } catch {
      setState('error')
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
          <p className="mt-4 text-sm text-muted-foreground">Set a new password</p>
        </div>

        <Card className="w-full">
          <CardHeader className="pb-4">
            <CardTitle className="text-xl">Reset password</CardTitle>
            <CardDescription>Enter your new password below</CardDescription>
          </CardHeader>
          <CardContent>
            {state === 'success' && (
              <div className="space-y-3">
                <p className="text-sm text-[hsl(var(--ec-success))] font-medium">
                  Password reset successfully!
                </p>
                <p className="text-sm text-muted-foreground">
                  Your password has been updated. You can now sign in with your new password.
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
                  Invalid or expired reset link.
                </p>
                <p className="text-sm text-muted-foreground">
                  This link may have expired. Please request a new password reset.
                </p>
                <Link
                  to="/forgot-password"
                  className="text-sm text-[hsl(var(--ec-primary))] hover:underline font-medium"
                >
                  Request new reset link
                </Link>
              </div>
            )}

            {state === 'form' && (
              <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
                {/* New password */}
                <div className="space-y-1.5">
                  <Label htmlFor="new_password">New password</Label>
                  <Input
                    id="new_password"
                    type="password"
                    autoComplete="new-password"
                    placeholder="Min. 8 characters"
                    {...register('new_password')}
                    aria-invalid={!!errors.new_password}
                  />
                  {errors.new_password && (
                    <p className="text-destructive text-sm">{errors.new_password.message}</p>
                  )}
                </div>

                {/* Confirm password */}
                <div className="space-y-1.5">
                  <Label htmlFor="confirm_password">Confirm new password</Label>
                  <Input
                    id="confirm_password"
                    type="password"
                    autoComplete="new-password"
                    placeholder="Re-enter your new password"
                    {...register('confirm_password')}
                    aria-invalid={!!errors.confirm_password}
                  />
                  {errors.confirm_password && (
                    <p className="text-destructive text-sm">
                      {errors.confirm_password.message}
                    </p>
                  )}
                </div>

                {/* Submit */}
                <Button
                  type="submit"
                  disabled={isSubmitting || !token}
                  className="w-full bg-[hsl(var(--ec-primary))] hover:bg-[hsl(var(--ec-primary))]/90 text-white min-h-[44px]"
                >
                  {isSubmitting ? 'Resetting...' : 'Reset password'}
                </Button>
              </form>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
