import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/_auth/demands')({
  component: () => (
    <div className="p-8">
      <h1 className="text-2xl font-bold text-foreground">Demands</h1>
      <p className="text-sm text-muted-foreground mt-2">Coming in Phase 5.</p>
    </div>
  ),
})
