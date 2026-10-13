import { useCallback, useEffect, useState } from 'react'
import { api } from '@/lib/api'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Select } from '@/components/ui/select'
import { Label } from '@/components/ui/label'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { PageHeader } from '@/components/layout'
import {
  Plus, RotateCw, Trash2, ListTodo, Circle, Timer, CheckCircle2, Inbox, MessageSquarePlus,
} from 'lucide-react'
import { TASK_STATUSES, PRIORITIES, taskStatusVariant, priorityVariant, humanize, formatTime } from '@/lib/constants'

function StatCard({ icon: Icon, label, value }) {
  return (
    <Card>
      <CardContent className="flex items-center gap-3 p-5">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-muted">
          <Icon className="h-4 w-4 text-muted-foreground" />
        </div>
        <div>
          <div className="text-2xl font-semibold leading-none">{value}</div>
          <div className="mt-1 text-xs text-muted-foreground">{label}</div>
        </div>
      </CardContent>
    </Card>
  )
}

export default function DashboardPage({ projects, activeProject, setActiveProject }) {
  const [tasks, setTasks] = useState([])
  const [stats, setStats] = useState({ total: 0, todo: 0, inProgress: 0, done: 0 })
  const [activity, setActivity] = useState([])
  const [filter, setFilter] = useState('ALL')
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [taskModal, setTaskModal] = useState(false)
  const [detail, setDetail] = useState(null)
  const [comments, setComments] = useState([])

  const load = useCallback(async () => {
    setLoading(true)
    try {
      setError('')
      const query = activeProject ? `?project_id=${activeProject}` : ''
      const [t, s, a] = await Promise.all([
        api.get(`/tasks${query}`),
        api.get('/tasks/stats'),
        api.get('/activity?limit=10'),
      ])
      setTasks(t); setStats(s); setActivity(a)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [activeProject])

  useEffect(() => { load() }, [load])

  const visible = filter === 'ALL' ? tasks : tasks.filter((t) => t.status === filter)

  const advance = async (task) => {
    setBusy(true)
    const next = task.status === 'TODO' ? 'IN_PROGRESS' : task.status === 'IN_PROGRESS' ? 'DONE' : 'TODO'
    try {
      await api.put(`/tasks/${task.id}`, { status: next })
      await load()
    } catch (e) { setError(e.message) } finally { setBusy(false) }
  }

  const remove = async (task) => {
    setBusy(true)
    try {
      await api.del(`/tasks/${task.id}`)
      if (detail?.id === task.id) setDetail(null)
      await load()
    } catch (e) { setError(e.message) } finally { setBusy(false) }
  }

  const createTask = async (e) => {
    e.preventDefault(); setBusy(true)
    const data = new FormData(e.currentTarget)
    const body = {
      title: data.get('title'),
      description: data.get('description') || '',
      priority: data.get('priority'),
      assignee: data.get('assignee') || 'Unassigned',
      status: 'TODO',
    }
    if (activeProject) body.project_id = activeProject
    try {
      await api.post('/tasks', body)
      setTaskModal(false)
      await load()
    } catch (err) { setError(err.message) } finally { setBusy(false) }
  }

  const openDetail = async (task) => {
    setDetail(task)
    try { setComments(await api.get(`/tasks/${task.id}/comments`)) } catch (e) { setError(e.message) }
  }

  const addComment = async (e) => {
    e.preventDefault(); setBusy(true)
    const data = new FormData(e.currentTarget)
    try {
      const comment = await api.post(`/tasks/${detail.id}/comments`, {
        author: data.get('author') || 'Berth Crew',
        content: data.get('content'),
      })
      setComments((cs) => [...cs, comment])
      e.currentTarget.reset()
      await load()
    } catch (err) { setError(err.message) } finally { setBusy(false) }
  }

  const projectById = (id) => projects.find((p) => p.id === id)

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow={activeProject ? `Project / ${projectById(activeProject)?.name || ''}` : 'Workspace / Overview'}
        title={activeProject ? projectById(activeProject)?.name || 'Project' : 'All tasks'}
        description={activeProject ? 'Tasks scoped to this project.' : 'Everything across your workspace.'}
        actions={
          <Button onClick={() => setTaskModal(true)} disabled={busy}>
            <Plus /> New task
          </Button>
        }
      />

      {error && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard icon={ListTodo} label="Total tasks" value={stats.total} />
        <StatCard icon={Circle} label="To do" value={stats.todo} />
        <StatCard icon={Timer} label="In progress" value={stats.inProgress} />
        <StatCard icon={CheckCircle2} label="Completed" value={stats.done} />
      </div>

      <div className="grid gap-6 xl:grid-cols-[1fr_320px]">
        <Card>
          <CardHeader className="flex-row items-center justify-between space-y-0">
            <div>
              <CardTitle className="text-base">Tasks</CardTitle>
              <CardDescription>Track work across every project.</CardDescription>
            </div>
            <Tabs value={filter} onValueChange={setFilter}>
              <TabsList>
                {['ALL', ...TASK_STATUSES].map((s) => (
                  <TabsTrigger key={s} value={s} className="text-xs">{s === 'ALL' ? 'All' : humanize(s)}</TabsTrigger>
                ))}
              </TabsList>
            </Tabs>
          </CardHeader>
          <CardContent className="p-0">
            {loading ? (
              <div className="flex items-center justify-center py-16 text-sm text-muted-foreground">Loading tasks…</div>
            ) : visible.length === 0 ? (
              <div className="flex flex-col items-center gap-2 py-16 text-center">
                <Inbox className="h-8 w-8 text-muted-foreground/50" />
                <p className="text-sm font-medium">{tasks.length ? 'No tasks in this filter.' : 'No tasks yet.'}</p>
                <p className="text-xs text-muted-foreground">{tasks.length ? 'Try a different status filter.' : 'Create your first task to get started.'}</p>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow className="hover:bg-transparent">
                    <TableHead className="pl-6">Task</TableHead>
                    <TableHead>Project</TableHead>
                    <TableHead>Assignee</TableHead>
                    <TableHead>Priority</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="pr-6 text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {visible.map((task) => (
                    <TableRow key={task.id}>
                      <TableCell className="pl-6">
                        <button className="text-left" onClick={() => openDetail(task)}>
                          <div className="font-medium hover:underline">{task.title}</div>
                          {task.description && <div className="mt-0.5 line-clamp-1 text-xs text-muted-foreground">{task.description}</div>}
                        </button>
                      </TableCell>
                      <TableCell className="text-muted-foreground">{projectById(task.project_id)?.name || '—'}</TableCell>
                      <TableCell className="text-muted-foreground">{task.assignee}</TableCell>
                      <TableCell><Badge variant={priorityVariant[task.priority]}>{humanize(task.priority)}</Badge></TableCell>
                      <TableCell><Badge variant={taskStatusVariant[task.status]}>{humanize(task.status)}</Badge></TableCell>
                      <TableCell className="pr-6 text-right">
                        <div className="flex justify-end gap-1">
                          <Button variant="ghost" size="icon" onClick={() => advance(task)} disabled={busy} title="Advance status">
                            <RotateCw />
                          </Button>
                          <Button variant="ghost" size="icon" onClick={() => remove(task)} disabled={busy} title="Delete task" className="text-muted-foreground hover:text-destructive">
                            <Trash2 />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Activity</CardTitle>
            <CardDescription>Latest workspace events.</CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            {activity.length === 0 ? (
              <div className="px-6 py-10 text-center text-sm text-muted-foreground">
                No activity yet. Actions will appear here.
              </div>
            ) : (
              <div className="divide-y">
                {activity.map((event) => (
                  <div key={event.id} className="flex gap-3 px-6 py-3">
                    <div className="mt-0.5 h-1.5 w-1.5 flex-none rounded-full bg-muted-foreground/40" />
                    <div className="min-w-0">
                      <div className="truncate text-xs font-medium">{event.summary}</div>
                      <div className="mt-0.5 text-xs text-muted-foreground">{event.actor} · {formatTime(event.created_at)}</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Dialog open={taskModal} onOpenChange={setTaskModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New task</DialogTitle>
            <DialogDescription>
              {activeProject ? `Will be added to ${projectById(activeProject)?.name}.` : 'Will be added without a project.'}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={createTask} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="task-title">Title</Label>
              <Input id="task-title" name="title" required placeholder="e.g. Configure production ingress" />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="task-description">Description</Label>
              <Textarea id="task-description" name="description" placeholder="What needs to be done?" />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label htmlFor="task-priority">Priority</Label>
                <Select id="task-priority" name="priority" defaultValue="MEDIUM">
                  {PRIORITIES.map((p) => <option key={p}>{p}</option>)}
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="task-assignee">Assignee</Label>
                <Input id="task-assignee" name="assignee" placeholder="Unassigned" />
              </div>
            </div>
            <Button type="submit" className="w-full" disabled={busy}>{busy ? 'Saving…' : 'Create task'}</Button>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={!!detail} onOpenChange={(open) => !open && setDetail(null)}>
        <DialogContent className="max-w-xl">
          {detail && (
            <>
              <DialogHeader>
                <DialogTitle>{detail.title}</DialogTitle>
                <DialogDescription>{detail.description || 'No description.'}</DialogDescription>
              </DialogHeader>
              <div className="flex flex-wrap gap-2">
                <Badge variant={taskStatusVariant[detail.status]}>{humanize(detail.status)}</Badge>
                <Badge variant={priorityVariant[detail.priority]}>{humanize(detail.priority)}</Badge>
                <Badge variant="outline">{detail.assignee}</Badge>
                {projectById(detail.project_id) && <Badge variant="outline">{projectById(detail.project_id).name}</Badge>}
              </div>
              <div className="space-y-2">
                <div className="text-sm font-medium">Discussion</div>
                {comments.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No comments yet.</p>
                ) : (
                  <div className="max-h-48 space-y-2 overflow-y-auto rounded-lg border p-3">
                    {comments.map((c) => (
                      <div key={c.id} className="rounded-md bg-muted/60 px-3 py-2">
                        <div className="flex items-baseline gap-2">
                          <span className="text-xs font-semibold">{c.author}</span>
                          <span className="text-xs text-muted-foreground">{formatTime(c.created_at)}</span>
                        </div>
                        <p className="mt-1 text-sm">{c.content}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
              <form onSubmit={addComment} className="flex items-end gap-2">
                <div className="w-36 space-y-1.5">
                  <Label htmlFor="comment-author" className="sr-only">Author</Label>
                  <Input id="comment-author" name="author" placeholder="Berth Crew" />
                </div>
                <div className="flex-1 space-y-1.5">
                  <Label htmlFor="comment-content" className="sr-only">Comment</Label>
                  <Input id="comment-content" name="content" required placeholder="Say something useful" />
                </div>
                <Button type="submit" size="icon" disabled={busy} title="Add comment"><MessageSquarePlus /></Button>
              </form>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
