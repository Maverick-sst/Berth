import { useCallback, useEffect, useState } from 'react'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { PageHeader } from '@/components/layout'
import { Plus, CheckCircle2, XCircle, Send, GitBranch, Inbox, RotateCcw } from 'lucide-react'
import { releaseStatusVariant, humanize, formatTime } from '@/lib/constants'

const NEXT_STEP = {
  PLANNED: 'Mark READY when all tasks are done',
  READY: 'Start a deployment',
  DEPLOYING: 'Awaiting deployment result',
  DEPLOYED: 'Shipped',
  FAILED: 'Retry: move back to PLANNED',
}

export default function ReleasesPage({ projects }) {
  const [releases, setReleases] = useState([])
  const [deployments, setDeployments] = useState([])
  const [detail, setDetail] = useState(null)
  const [createOpen, setCreateOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      setError('')
      const [r, d] = await Promise.all([api.get('/releases'), api.get('/deployments')])
      setReleases(r); setDeployments(d)
    } catch (e) { setError(e.message) } finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  const openDetail = async (release) => {
    try { setDetail(await api.get(`/releases/${release.id}`)) } catch (e) { setError(e.message) }
  }

  const transition = async (release, status) => {
    setBusy(true)
    try {
      await api.put(`/releases/${release.id}`, { status })
      setDetail(null)
      await load()
    } catch (e) { setError(e.message) } finally { setBusy(false) }
  }

  const createRelease = async (e) => {
    e.preventDefault(); setBusy(true)
    const data = new FormData(e.currentTarget)
    const projectId = data.get('project_id')
    try {
      await api.post('/releases', {
        name: data.get('name'),
        description: data.get('description') || '',
        project_id: Number(projectId),
      })
      setCreateOpen(false)
      await load()
    } catch (err) { setError(err.message) } finally { setBusy(false) }
  }

  const startDeployment = async (release) => {
    setBusy(true)
    const environment = detail?.deployEnv || 'dev'
    try {
      await api.post(`/releases/${release.id}/deployments`, { environment })
      setDetail(null)
      await load()
    } catch (e) { setError(e.message) } finally { setBusy(false) }
  }

  if (loading) {
    return <div className="py-24 text-center text-sm text-muted-foreground">Loading releases…</div>
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Workspace / Releases"
        title="Releases"
        description="Prepare releases, check readiness, and track every deployment attempt."
        actions={
          <Button onClick={() => setCreateOpen(true)} disabled={!projects.length} title={projects.length ? '' : 'Create a project first'}>
            <Plus /> New release
          </Button>
        }
      />

      {error && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">{error}</div>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">All releases</CardTitle>
          <CardDescription>Status transitions are validated by the server.</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {releases.length === 0 ? (
            <div className="flex flex-col items-center gap-2 py-16 text-center">
              <Inbox className="h-8 w-8 text-muted-foreground/50" />
              <p className="text-sm font-medium">No releases yet.</p>
              <p className="text-xs text-muted-foreground">Create one to start tracking readiness and deployments.</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead className="pl-6">Release</TableHead>
                  <TableHead>Project</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead className="pr-6 text-right">Next step</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {releases.map((r) => (
                  <TableRow key={r.id} className="cursor-pointer" onClick={() => openDetail(r)}>
                    <TableCell className="pl-6">
                      <div className="flex items-center gap-2 font-medium hover:underline">
                        <GitBranch className="h-3.5 w-3.5 text-muted-foreground" /> {r.name}
                      </div>
                      {r.description && <div className="mt-0.5 line-clamp-1 text-xs text-muted-foreground">{r.description}</div>}
                    </TableCell>
                    <TableCell className="text-muted-foreground">{projects.find((p) => p.id === r.project_id)?.name || r.project_id}</TableCell>
                    <TableCell><Badge variant={releaseStatusVariant[r.status]}>{humanize(r.status)}</Badge></TableCell>
                    <TableCell className="text-muted-foreground">{formatTime(r.created_at)}</TableCell>
                    <TableCell className="pr-6 text-right text-xs text-muted-foreground">{NEXT_STEP[r.status]}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Deployment history</CardTitle>
          <CardDescription>Every reported attempt — successes and failures alike.</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {deployments.length === 0 ? (
            <div className="px-6 py-10 text-center text-sm text-muted-foreground">No deployments recorded yet.</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead className="pl-6">Release</TableHead>
                  <TableHead>Environment</TableHead>
                  <TableHead>Commit</TableHead>
                  <TableHead>Result</TableHead>
                  <TableHead>Started</TableHead>
                  <TableHead className="pr-6">Detail</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {deployments.map((d) => (
                  <TableRow key={d.id}>
                    <TableCell className="pl-6 font-medium">#{d.release_id}</TableCell>
                    <TableCell><Badge variant="outline">{d.environment}</Badge></TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">{d.commit_sha || '—'}</TableCell>
                    <TableCell>
                      {d.status === 'SUCCEEDED' && <Badge variant="success"><CheckCircle2 className="mr-1 h-3 w-3" />Succeeded</Badge>}
                      {d.status === 'FAILED' && <Badge variant="destructive"><XCircle className="mr-1 h-3 w-3" />Failed</Badge>}
                      {d.status === 'IN_PROGRESS' && <Badge variant="warning"><Send className="mr-1 h-3 w-3" />Running</Badge>}
                    </TableCell>
                    <TableCell className="text-muted-foreground">{formatTime(d.started_at)}</TableCell>
                    <TableCell className="pr-6 max-w-56 truncate text-xs text-muted-foreground" title={d.failure_reason || ''}>{d.failure_reason || d.image_ref || '—'}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New release</DialogTitle>
            <DialogDescription>Releases start as PLANNED. Attach tasks, then mark READY when they are done.</DialogDescription>
          </DialogHeader>
          <form onSubmit={createRelease} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="release-project">Project</Label>
              <select
                id="release-project"
                name="project_id"
                required
                className="flex h-9 w-full rounded-md border border-input bg-card px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="release-name">Name</Label>
              <Input id="release-name" name="name" required placeholder="e.g. v1.2.0" />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="release-description">Description</Label>
              <Textarea id="release-description" name="description" placeholder="What ships in this release?" />
            </div>
            <Button type="submit" className="w-full" disabled={busy}>{busy ? 'Saving…' : 'Create release'}</Button>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={!!detail} onOpenChange={(open) => !open && setDetail(null)}>
        <DialogContent className="max-w-xl">
          {detail && (
            <>
              <DialogHeader>
                <DialogTitle className="flex items-center gap-2">{detail.name} <Badge variant={releaseStatusVariant[detail.status]}>{humanize(detail.status)}</Badge></DialogTitle>
                <DialogDescription>{detail.description || 'No description.'}</DialogDescription>
              </DialogHeader>

              <Card>
                <CardHeader className="p-4 pb-2">
                  <CardTitle className="text-sm">Readiness</CardTitle>
                </CardHeader>
                <CardContent className="p-4 pt-0">
                  {detail.readiness.ready ? (
                    <div className="flex items-center gap-2 text-sm font-medium text-success">
                      <CheckCircle2 className="h-4 w-4" /> Ready — all {detail.readiness.total_tasks} tasks done
                    </div>
                  ) : (
                    <div className="space-y-1.5">
                      {detail.readiness.blockers.map((b) => (
                        <div key={b} className="flex items-center gap-2 text-sm text-warning">
                          <XCircle className="h-4 w-4" /> {b}
                        </div>
                      ))}
                    </div>
                  )}
                  <div className="mt-2 text-xs text-muted-foreground">
                    {detail.readiness.done_tasks} of {detail.readiness.total_tasks} tasks done
                  </div>
                </CardContent>
              </Card>

              <div className="space-y-2">
                <div className="text-sm font-medium">Tasks in this release</div>
                {detail.tasks.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No tasks attached.</p>
                ) : (
                  <div className="max-h-40 space-y-1.5 overflow-y-auto rounded-lg border p-3">
                    {detail.tasks.map((t) => (
                      <div key={t.id} className="flex items-center justify-between text-sm">
                        <span className="truncate">{t.title}</span>
                        <Badge variant={t.status === 'DONE' ? 'success' : 'secondary'} className="ml-2 flex-none">{humanize(t.status)}</Badge>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="flex flex-wrap gap-2">
                {detail.status === 'PLANNED' && (
                  <Button onClick={() => transition(detail, 'READY')} disabled={busy || !detail.readiness.ready} title={!detail.readiness.ready ? 'Finish all tasks first' : ''}>
                    <CheckCircle2 /> Mark READY
                  </Button>
                )}
                {detail.status === 'READY' && (
                  <>
                    <Button onClick={() => startDeployment(detail)} disabled={busy}><Send /> Start deployment</Button>
                    <Button variant="outline" onClick={() => transition(detail, 'PLANNED')} disabled={busy}>Back to PLANNED</Button>
                  </>
                )}
                {detail.status === 'FAILED' && (
                  <Button onClick={() => transition(detail, 'PLANNED')} disabled={busy}><RotateCcw /> Retry from PLANNED</Button>
                )}
                {detail.status === 'DEPLOYING' && <p className="text-sm text-muted-foreground py-2">Awaiting deployment result…</p>}
                {detail.status === 'DEPLOYED' && <p className="text-sm text-success py-2 font-medium">This release shipped.</p>}
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
