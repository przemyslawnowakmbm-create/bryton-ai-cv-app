import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/_auth/candidates')({
  component: () => (
    <div className="p-8">
      <h1 className="text-2xl font-bold text-foreground">Candidates</h1>
      <p className="text-sm text-muted-foreground mt-2">Coming in Phase 4.</p>
    </div>
  ),
})
