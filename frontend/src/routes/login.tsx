import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/login')({
  component: LoginPage,
})

function LoginPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="w-full max-w-md px-8 py-12">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-ec-primary mb-2">
            Bryton AI CV App
          </h1>
          <div className="ec-accent-line mx-auto w-24 mt-3" />
          <p className="mt-4 text-sm text-muted-foreground">
            Sign in to your account
          </p>
        </div>
        <div className="bg-card rounded-lg border border-border p-6 shadow-sm">
          <p className="text-sm text-muted-foreground text-center">
            Login form coming in Phase 2.
          </p>
        </div>
      </div>
    </div>
  )
}
