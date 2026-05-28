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

const candidateRegisterSchema = z
  .object({
    display_name: z.string().optional(),
    email: z.string().email('Please enter a valid email address'),
    password: z.string().min(8, 'Password must be at least 8 characters'),
    confirm_password: z.string().min(1, 'Please confirm your password'),
    gdpr_consent: z.literal(true, {
      errorMap: () => ({ message: 'You must accept the GDPR consent to continue' }),
    }),
  })
  .refine((d) => d.password === d.confirm_password, {
    message: 'Passwords do not match',
    path: ['confirm_password'],
  })

type CandidateRegisterForm = z.infer<typeof candidateRegisterSchema>

export const Route = createFileRoute('/register/candidate')({
  component: CandidateRegisterPage,
})

function CandidateRegisterPage() {
  const [success, setSuccess] = useState(false)
  const [serverError, setServerError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<CandidateRegisterForm>({
    resolver: zodResolver(candidateRegisterSchema),
  })

  async function onSubmit(data: CandidateRegisterForm) {
    setServerError(null)
    try {
      await apiMutate('/auth/register/candidate', 'POST', {
        email: data.email,
        password: data.password,
        display_name: data.display_name || undefined,
        gdpr_consent: true,
      })
      setSuccess(true)
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      if (msg.includes('400') || msg.includes('409') || msg.toLowerCase().includes('exists')) {
        setServerError('An account with that email is already registered.')
      } else {
        setServerError('Registration failed. Please try again.')
      }
    }
  }

  if (success) {
    return (
      <div className="min-h-dvh flex items-center justify-center bg-background px-4">
        <div className="w-full max-w-md">
          <Card>
            <CardHeader>
              <CardTitle className="text-xl text-[hsl(var(--ec-primary))]">
                Check your email
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm text-muted-foreground">
                We&apos;ve sent a verification link to your email address. Please click the link
                to activate your account before signing in.
              </p>
              <Link
                to="/login"
                className="text-sm text-[hsl(var(--ec-primary))] hover:underline font-medium"
              >
                Back to sign in
              </Link>
            </CardContent>
          </Card>
        </div>
      </div>
    )
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
          <p className="mt-4 text-sm text-muted-foreground">Candidate registration</p>
        </div>

        <Card className="w-full">
          <CardHeader className="pb-4">
            <CardTitle className="text-xl">Create candidate account</CardTitle>
            <CardDescription>
              Register as a candidate to browse and apply for opportunities
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
              {/* Display name (optional) */}
              <div className="space-y-1.5">
                <Label htmlFor="display_name">
                  Full name{' '}
                  <span className="text-muted-foreground font-normal">(optional)</span>
                </Label>
                <Input
                  id="display_name"
                  type="text"
                  autoComplete="name"
                  placeholder="Jane Smith"
                  {...register('display_name')}
                />
              </div>

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
                <Label htmlFor="password">Password</Label>
                <Input
                  id="password"
                  type="password"
                  autoComplete="new-password"
                  placeholder="Min. 8 characters"
                  {...register('password')}
                  aria-invalid={!!errors.password}
                />
                {errors.password && (
                  <p className="text-destructive text-sm">{errors.password.message}</p>
                )}
              </div>

              {/* Confirm password */}
              <div className="space-y-1.5">
                <Label htmlFor="confirm_password">Confirm password</Label>
                <Input
                  id="confirm_password"
                  type="password"
                  autoComplete="new-password"
                  placeholder="Re-enter your password"
                  {...register('confirm_password')}
                  aria-invalid={!!errors.confirm_password}
                />
                {errors.confirm_password && (
                  <p className="text-destructive text-sm">
                    {errors.confirm_password.message}
                  </p>
                )}
              </div>

              {/* GDPR consent */}
              <div className="space-y-1.5 pt-2">
                <div className="flex items-start gap-3">
                  <input
                    id="gdpr_consent"
                    type="checkbox"
                    className="mt-1 h-4 w-4 rounded border-input accent-[hsl(var(--ec-primary))] cursor-pointer focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                    {...register('gdpr_consent')}
                    aria-invalid={!!errors.gdpr_consent}
                  />
                  <Label htmlFor="gdpr_consent" className="text-sm font-normal leading-snug cursor-pointer">
                    I consent to the processing of my personal data in accordance with{' '}
                    <abbr title="General Data Protection Regulation">GDPR</abbr> regulations
                  </Label>
                </div>
                {errors.gdpr_consent && (
                  <p className="text-destructive text-sm">{errors.gdpr_consent.message}</p>
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
                {isSubmitting ? 'Creating account...' : 'Create candidate account'}
              </Button>
            </form>

            <p className="mt-4 text-center text-sm text-muted-foreground">
              Already have an account?{' '}
              <Link
                to="/login"
                className="text-[hsl(var(--ec-primary))] hover:underline font-medium"
              >
                Sign in
              </Link>
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
