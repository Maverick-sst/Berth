import React,{useEffect,useState,useCallback} from 'react'; import {createRoot} from 'react-dom/client'; import './styles.css';
const API='/api';
const STATUS_OPTIONS=['ALL','TODO','IN_PROGRESS','DONE'];
const label=(x)=>x==='ALL'?'All':x.replace('_',' ').toLowerCase().replace(/\b\w/g,c=>c.toUpperCase());
async function apiFetch(path, options){
  const response=await fetch(path, options);
  if(!response.ok){let detail='';try{detail=(await response.json()).detail}catch{detail=''};throw Error(detail||`Request failed (${response.status})`)}
  return response;
}
function App(){
  const [projects,setProjects]=useState([]),[activeProject,setActiveProject]=useState(null),[tasks,setTasks]=useState([]),[stats,setStats]=useState({total:0,todo:0,inProgress:0,done:0}),[filter,setFilter]=useState('ALL'),[showForm,setShowForm]=useState(false),[showTaskDetail,setShowTaskDetail]=useState(null),[activity,setActivity]=useState([]),[comments,setComments]=useState([]),[loading,setLoading]=useState(true),[busy,setBusy]=useState(false),[error,setError]=useState('');
  const load=useCallback(async()=>{
    setLoading(true);
    try{
      setError('');
      const url=activeProject?`${API}/tasks?project_id=${activeProject}`:`${API}/tasks`;
      const [a,b,c]=await Promise.all([apiFetch(url),apiFetch(`${API}/tasks/stats`),apiFetch(`${API}/activity?limit=12`)]);
      setTasks(await a.json());setStats(await b.json());setActivity(await c.json());
    }catch(e){setError(e.message)}finally{setLoading(false)}
  },[activeProject]);
  const loadProjects=useCallback(async()=>{
    try{setProjects(await (await apiFetch(`${API}/projects`)).json())}catch(e){setError(e.message)}
  },[]);
  useEffect(()=>{loadProjects()},[loadProjects]);
  useEffect(()=>{load()},[load]);
  const visible=filter==='ALL'?tasks:tasks.filter(t=>t.status===filter);
  const update=async(t)=>{
    setBusy(true);
    const next=t.status==='TODO'?'IN_PROGRESS':t.status==='IN_PROGRESS'?'DONE':'TODO';
    try{await apiFetch(`${API}/tasks/${t.id}`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({status:next})});await load()}
    catch(e){setError(e.message)}finally{setBusy(false)}
  };
  const remove=async(t)=>{
    setBusy(true);
    try{await apiFetch(`${API}/tasks/${t.id}`,{method:'DELETE'});await load();if(showTaskDetail?.id===t.id)setShowTaskDetail(null)}
    catch(e){setError(e.message)}finally{setBusy(false)}
  };
  const openDetail=async(t)=>{
    setShowTaskDetail(t);
    try{setComments(await (await apiFetch(`${API}/tasks/${t.id}/comments`)).json())}catch(e){setError(e.message)}
  };
  const addComment=async(e)=>{
    e.preventDefault();setBusy(true);
    const f=new FormData(e.currentTarget);
    try{
      const comment=await (await apiFetch(`${API}/tasks/${showTaskDetail.id}/comments`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({author:f.get('author')||'Berth Crew',content:f.get('content')})})).json();
      setComments(cs=>[...cs,comment]);e.currentTarget.reset();await load();
    }catch(e2){setError(e2.message)}finally{setBusy(false)}
  };
  const create=async(e)=>{
    e.preventDefault();setBusy(true);
    const f=new FormData(e.currentTarget);
    const body={title:f.get('title'),description:f.get('description'),priority:f.get('priority'),assignee:f.get('assignee')||'Unassigned',status:'TODO'};
    if(activeProject)body.project_id=activeProject;
    try{
      await apiFetch(`${API}/tasks`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
      e.currentTarget.reset();setShowForm(false);await load();
    }catch(e2){setError(e2.message)}finally{setBusy(false)}
  };
  const createProject=async(e)=>{
    e.preventDefault();setBusy(true);
    const f=new FormData(e.currentTarget);
    try{
      const created=await (await apiFetch(`${API}/projects`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:f.get('name'),description:f.get('description')})})).json();
      setShowForm(false);await loadProjects();setActiveProject(created.id);
    }catch(e2){setError(e2.message)}finally{setBusy(false)}
  };
  return <div className="app">
    <aside className="sidebar">
      <div className="brand"><span className="brand-mark">B</span><div><b>Berth</b><small>Engineering work, docked</small></div></div>
      <nav><a className="active" href="#" onClick={(e)=>{e.preventDefault();setActiveProject(null)}}>▦ <span>All tasks</span></a></nav>
      <div className="projects-head"><b>Projects</b><button className="side-add" onClick={()=>setShowForm('project')}>＋</button></div>
      <nav className="projects-nav">
        {projects.map(p=><a key={p.id} href="#" className={activeProject===p.id?'active':''} onClick={(e)=>{e.preventDefault();setActiveProject(p.id)}}>◫ <span>{p.name}</span></a>)}
        {!projects.length&&<small className="side-empty">No projects yet</small>}
      </nav>
      <div className="side-bottom">
        <div className="upgrade"><strong>Dock your work.</strong><p>Plan tasks, cut releases, and keep a real deployment history.</p></div>
        <div className="profile"><div className="avatar">MB</div><div><b>Berth Crew</b><small>Demo identity</small></div></div>
      </div>
    </aside>
    <main className="main">
      <header>
        <div><p className="eyebrow">{activeProject?'PROJECT':'WORKSPACE'}{activeProject?' / '+(projects.find(p=>p.id===activeProject)?.name||''):' / OVERVIEW'}</p>
        <h1>{activeProject?projects.find(p=>p.id===activeProject)?.name||'Project':'All tasks'}</h1>
        <p className="muted">{activeProject?'Tasks scoped to this project.':'Everything across your workspace.'}</p></div>
        <button className="primary" onClick={()=>setShowForm('task')} disabled={busy}>＋ New task</button>
      </header>
      {error&&<div className="alert">⚠ {error}</div>}
      <section className="stats">
        <Stat label="Total tasks" value={stats.total} icon="▦"/>
        <Stat label="To do" value={stats.todo} icon="○"/>
        <Stat label="In progress" value={stats.inProgress} icon="◔"/>
        <Stat label="Completed" value={stats.done} icon="✓"/>
      </section>
      <section className="content-grid">
        <div className="panel tasks-panel">
          <div className="panel-head"><div><h2>Tasks</h2><p className="muted">{activeProject?'Project-scoped list.':'Track work across every project.'}</p></div>
          <div className="filters">{STATUS_OPTIONS.map(x=><button className={filter===x?'selected':''} onClick={()=>setFilter(x)} key={x}>{label(x)}</button>)}</div></div>
          {loading?<div className="empty">Loading tasks…</div>:visible.length?<div className="table-wrap"><table>
            <thead><tr><th>Task</th><th>Project</th><th>Assignee</th><th>Priority</th><th>Status</th><th></th></tr></thead>
            <tbody>{visible.map(t=><tr key={t.id}><td><div className="task-title"><span className={`dot ${t.status.toLowerCase()}`}></span><div><b>{t.title}</b><small>{t.description}</small></div></div></td>
              <td>{projects.find(p=>p.id===t.project_id)?.name||'—'}</td><td>{t.assignee}</td>
              <td><span className={`priority ${t.priority.toLowerCase()}`}>{t.priority}</span></td>
              <td><span className={`status ${t.status.toLowerCase()}`}>{label(t.status)}</span></td>
              <td><div className="row-actions"><button className="icon-btn" onClick={()=>openDetail(t)} disabled={busy} title="Open task">↧</button><button className="icon-btn" onClick={()=>update(t)} disabled={busy} title="Advance status">↻</button><button className="icon-btn danger" onClick={()=>remove(t)} disabled={busy} title="Delete task">🗑</button></div></td></tr>)}</tbody>
          </table></div>:<div className="empty">{tasks.length?'No tasks in this filter.':'No tasks yet. Create your first one.'}</div>}
        </div>
        <aside className="panel activity">
          <div className="panel-head"><div><h2>Workspace</h2><p className="muted">Quick facts.</p></div></div>
          <div className="fact-row"><span>Projects</span><b>{projects.length}</b></div>
          <div className="fact-row"><span>Tasks</span><b>{stats.total}</b></div>
          <div className="fact-row"><span>Completed</span><b>{stats.done}</b></div>
          <ActivityFeed activity={activity}/>
        </aside>
      </section>
      {showForm==='task'&&<div className="modal-backdrop"><form className="modal" onSubmit={create}>
        <div className="modal-head"><div><p className="eyebrow">CREATE TASK</p><h2>Add a new task</h2></div><button type="button" className="close" onClick={()=>setShowForm(false)}>×</button></div>
        <label>Task title<input name="title" required placeholder="e.g. Configure production ingress"/></label>
        <label>Description<textarea name="description" placeholder="What needs to be done?"/></label>
        <div className="form-row">
          <label>Priority<select name="priority"><option>LOW</option><option>MEDIUM</option><option>HIGH</option></select></label>
          <label>Assignee<input name="assignee" placeholder="Unassigned"/></label>
        </div>
        <p className="muted modal-note">{activeProject?`Will be added to project #${activeProject}.`:'Will be added without a project.'}</p>
        <button className="primary full" disabled={busy}>{busy?'Saving…':'Create task'}</button>
      </form></div>}
      {showForm==='project'&&<div className="modal-backdrop"><form className="modal" onSubmit={createProject}>
        <div className="modal-head"><div><p className="eyebrow">CREATE PROJECT</p><h2>Dock a new project</h2></div><button type="button" className="close" onClick={()=>setShowForm(false)}>×</button></div>
        <label>Project name<input name="name" required placeholder="e.g. Web Platform"/></label>
        <label>Description<textarea name="description" placeholder="What is this project about?"/></label>
        <button className="primary full" disabled={busy}>{busy?'Saving…':'Create project'}</button>
      </form></div>}
      {showTaskDetail&&<div className="modal-backdrop" onClick={()=>setShowTaskDetail(null)}><div className="modal" onClick={(e)=>e.stopPropagation()}>
        <div className="modal-head"><div><p className="eyebrow">TASK</p><h2>{showTaskDetail.title}</h2></div><button type="button" className="close" onClick={()=>setShowTaskDetail(null)}>×</button></div>
        <p className="muted">{showTaskDetail.description||'No description.'}</p>
        <div className="detail-grid">
          <div><small>Status</small><b>{label(showTaskDetail.status)}</b></div>
          <div><small>Priority</small><b>{showTaskDetail.priority}</b></div>
          <div><small>Assignee</small><b>{showTaskDetail.assignee}</b></div>
          <div><small>Project</small><b>{projects.find(p=>p.id===showTaskDetail.project_id)?.name||'—'}</b></div>
        </div>
        <h3>Discussion</h3>
        <div className="comment-list">{comments.length?comments.map(c=><div className="comment" key={c.id}><b>{c.author}</b><small>{new Date(c.created_at).toLocaleString()}</small><p>{c.content}</p></div>):<p className="muted">No comments yet.</p>}</div>
        <form onSubmit={addComment}><div className="form-row">
          <label>Author<input name="author" placeholder="Berth Crew"/></label>
          <label>Comment<input name="content" required placeholder="Say something useful"/></label>
        </div><button className="primary full" disabled={busy}>{busy?'Posting…':'Add comment'}</button></form>
      </div></div>}
    </main>
  </div>;
}
function ActivityFeed({activity}){return activity.length?<div>{activity.map(e=><div className="activity-row" key={e.id}><span className="activity-icon">{e.action==='created'?'＋':e.action==='deleted'?'−':e.action==='commented'?'💬':'✎'}</span><div><b>{e.summary}</b><small>{e.actor} · {new Date(e.created_at).toLocaleString()}</small></div></div>)}</div>:<div className="empty">No activity yet. Actions will appear here.</div>}
function Stat({label,value,icon}){return <div className="stat"><div className="stat-icon">{icon}</div><div><small>{label}</small><strong>{value}</strong><span>live from API</span></div></div>}
createRoot(document.getElementById('root')).render(<App/>);
