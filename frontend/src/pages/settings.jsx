import { useEffect, useState } from 'react'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { PageHeader } from '@/components/layout'
import { Plus, Trash2 } from 'lucide-react'
import { formatTime } from '@/lib/constants'

export default function SettingsPage({ projects, setActiveProject }) {
  const [createOpen, setCreateOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const createProject = async (e) => {
    e.preventDefault(); setBusy(true)
    const data = new FormData(e.currentTarget)
    try {
      await api.post('/projects', { name: data.get('name'), description: data.get('description') || '' })
      setCreateOpen(false)
      window.dispatchEvent(new Event('berth:projects-changed'))
    } catch (err) { setError(err.message) } finally { setBusy(false) }
  }

  const removeProject = async (project) => {
    setBusy(true)
    try {
      await api.del(`/projects/${project.id}`)
      window.dispatchEvent(new Event('berth:projects-changed'))
    } catch (e) {
      setError(e.message)
    } finally { setBusy(false) }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Workspace / Projects"
        title="Projects"
        description="Group tasks into projects. A project with tasks cannot be deleted."
        actions={<Button onClick={() => setCreateOpen(true)}><Plus /> New project</Button>}
      />
      {error && <div className="rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">{error}</div>}
      <Card>
        <CardHeader><CardTitle className="text-base">Your projects</CardTitle><CardDescription>Task lists, releases, and deployment history are scoped to projects.</CardDescription></CardHeader>
        <CardContent className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {projects.length === 0 && <p className="py-6 text-sm text-muted-foreground">No projects yet — create one to get started.</p>}
          {projects.map((p) => (
            <div key={p.id} className="rounded-lg border p-4">
              <div className="flex items-start justify-between">
                <div className="min-w-0">
                  <div className="truncate text-sm font-medium">{p.name}</div>
                  <div className="mt-0.5 line-clamp-2 text-xs text-muted-foreground">{p.description || 'No description.'}</div>
                </div>
                <Button variant="ghost" size="icon" className="h-7 w-7 flex-none text-muted-foreground hover:text-destructive" onClick={() => removeProject(p)} disabled={busy} title="Delete project">
                  <Trash2 />
                </Button>
              </div>
              <div className="mt-3 text-xs text-muted-foreground">Created {formatTime(p.created_at)}</div>
            </div>
          ))}
        </CardContent>
      </Card>
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New project</DialogTitle>
            <DialogDescription>Projects group related tasks and releases.</DialogDescription>
          </DialogHeader>
          <form onSubmit={createProject} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="project-name">Name</Label>
              <Input id="project-name" name="name" required placeholder="e.g. Web Platform" />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="project-description">Description</Label>
              <Textarea id="project-description" name="description" placeholder="What is this project about?" />
            </div>
            <Button type="submit" className="w-full" disabled={busy}>{busy ? 'Saving…' : 'Create project'}</Button>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
