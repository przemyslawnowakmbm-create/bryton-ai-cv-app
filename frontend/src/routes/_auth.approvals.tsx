import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/_auth/approvals')({
  component: () => (
    <div className="p-8">
      <h1 className="text-2xl font-bold text-foreground">Approvals</h1>
      <p className="text-sm text-muted-foreground mt-2">Coming in Phase 2.</p>
    </div>
  ),
})
