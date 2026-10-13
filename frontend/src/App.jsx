import { useCallback, useEffect, useState } from 'react'
import { api } from '@/lib/api'
import { Sidebar, SidebarHeader, SidebarSection, SidebarItem, PageShell } from '@/components/layout'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import DashboardPage from '@/pages/dashboard'
import ReleasesPage from '@/pages/releases'
import SettingsPage from '@/pages/settings'
import { LayoutDashboard, GitBranch, FolderKanban } from 'lucide-react'
import { releaseStatusVariant } from '@/lib/constants'

const PAGES = {
  tasks: DashboardPage,
  releases: ReleasesPage,
  projects: SettingsPage,
}

export default function App() {
  const [page, setPage] = useState('tasks')
  const [projects, setProjects] = useState([])
  const [releases, setReleases] = useState([])
  const [activeProject, setActiveProject] = useState(null)
  const [bootError, setBootError] = useState('')

  const loadProjects = useCallback(async () => {
    try {
      setProjects(await api.get('/projects'))
    } catch (e) {
      setBootError(e.message)
    }
  }, [])

  const loadReleases = useCallback(async () => {
    try {
      setReleases(await api.get('/releases'))
    } catch (e) {
      setBootError(e.message)
    }
  }, [])

  useEffect(() => {
    loadProjects()
    loadReleases()
    const onProjectsChanged = () => loadProjects()
    window.addEventListener('berth:projects-changed', onProjectsChanged)
    const poll = setInterval(loadReleases, 30000)
    return () => {
      window.removeEventListener('berth:projects-changed', onProjectsChanged)
      clearInterval(poll)
    }
  }, [loadProjects, loadReleases])

  useEffect(() => {
    if (activeProject && !projects.some((p) => p.id === activeProject)) setActiveProject(null)
  }, [projects, activeProject])

  const Page = PAGES[page]

  return (
    <>
      <Sidebar>
        <SidebarHeader />
        <div className="flex-1 overflow-y-auto">
          <SidebarSection title="Workspace">
            <SidebarItem active={page === 'tasks' && !activeProject} onClick={() => setPage('tasks')}>
              <LayoutDashboard className="h-4 w-4 text-muted-foreground" /> All tasks
            </SidebarItem>
          </SidebarSection>
          <SidebarSection
            title="Projects"
            action={<Button variant="ghost" size="icon" className="h-5 w-5" onClick={() => setPage('projects')} title="Manage projects"><span className="text-base leading-none">＋</span></Button>}
          >
            {projects.map((p) => (
              <SidebarItem
                key={p.id}
                active={page === 'tasks' && activeProject === p.id}
                onClick={() => { setActiveProject(p.id); setPage('tasks') }}
              >
                <FolderKanban className="h-4 w-4 text-muted-foreground" /> {p.name}
              </SidebarItem>
            ))}
            {projects.length === 0 && <p className="px-2 py-1.5 text-xs text-muted-foreground">No projects yet</p>}
          </SidebarSection>
          <SidebarSection title="Releases">
            <SidebarItem active={page === 'releases'} onClick={() => setPage('releases')}>
              <GitBranch className="h-4 w-4 text-muted-foreground" /> Overview
            </SidebarItem>
            {releases.slice(0, 5).map((r) => (
              <SidebarItem key={r.id} onClick={() => setPage('releases')}>
                <span className="min-w-0 flex-1 truncate pl-1 text-muted-foreground">{r.name}</span>
                <Badge variant={releaseStatusVariant[r.status]} className="flex-none px-1.5 text-[10px]">{r.status}</Badge>
              </SidebarItem>
            ))}
            {releases.length === 0 && <p className="px-2 py-1.5 text-xs text-muted-foreground">No releases yet</p>}
          </SidebarSection>
        </div>
        <div className="border-t px-4 py-3">
          <div className="flex items-center gap-2.5">
            <div className="flex h-7 w-7 items-center justify-center rounded-full bg-muted text-xs font-semibold text-muted-foreground">BC</div>
            <div className="min-w-0">
              <div className="truncate text-xs font-medium">Berth Crew</div>
              <div className="text-[10px] text-muted-foreground">Demo identity</div>
            </div>
          </div>
        </div>
      </Sidebar>

      <PageShell>
        <div className="mx-auto max-w-6xl px-6 py-8 lg:px-10">
          {bootError && (
            <div className="mb-6 rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
              ⚠ {bootError} — is the backend running?
            </div>
          )}
          <Page projects={projects} activeProject={activeProject} setActiveProject={setActiveProject} />
        </div>
      </PageShell>
    </>
  )
}
