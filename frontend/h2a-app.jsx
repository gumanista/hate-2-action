/* hate2action — full app with role-based access */
const { useState, useEffect, useRef, useCallback, createContext, useContext } = React;

/* ══════════════════════════════════════════
   AUTH CONTEXT
══════════════════════════════════════════ */
const AuthContext = createContext(null);
function useAuth() { return useContext(AuthContext); }

const MOCK_USERS = [
  { id: 1, email: 'user@h2a.com',      password: 'user123', name: 'Alex User',      role: 'user'      },
  { id: 2, email: 'dev@h2a.com',       password: 'dev123',  name: 'Dev Admin',      role: 'developer' },
  { id: 3, email: 'dasha@h2a.com',     password: 'dasha',   name: 'Dasha Shevchuk', role: 'developer' },
];

function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try { return JSON.parse(localStorage.getItem('h2a_user') || 'null'); } catch { return null; }
  });

  const login = useCallback((email, password) => {
    const found = MOCK_USERS.find(u => u.email === email && u.password === password);
    if (!found) throw new Error('Invalid email or password');
    const { password: _, ...safe } = found;
    setUser(safe);
    localStorage.setItem('h2a_user', JSON.stringify(safe));
    return safe;
  }, []);

  const logout = useCallback(() => {
    setUser(null);
    localStorage.removeItem('h2a_user');
  }, []);

  const role = user?.role || 'guest';
  const isGuest = role === 'guest';
  const isUser  = role === 'user' || role === 'developer';
  const isDev   = role === 'developer';
  const can = { viewPublic: true, submitContent: isUser, viewAdmin: isDev };

  return (
    <AuthContext.Provider value={{ user, role, isGuest, isUser, isDev, can, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

/* ══════════════════════════════════════════
   DATA HOOK (real API)
══════════════════════════════════════════ */
function useData(fetchFn) {
  const [data, setData]     = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]   = useState(null);
  const reload = useCallback(async () => {
    setLoading(true); setError(null);
    try { setData(await fetchFn()); }
    catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { reload(); }, [reload]);
  return { data, loading, error, reload, setData };
}

/* ══════════════════════════════════════════
   ROUTER
══════════════════════════════════════════ */
function useRouter() {
  const [route, setRoute] = useState({ page: 'home' });
  const navigate = useCallback((page, params = {}) => {
    setRoute({ page, ...params });
    window.scrollTo(0, 0);
  }, []);
  return { route, navigate };
}

/* ══════════════════════════════════════════
   STATUS BADGE HELPER
══════════════════════════════════════════ */
function StatusBadge({ status }) {
  const map = {
    approved: { variant: 'teal',  label: 'Approved' },
    pending:  { variant: 'coral', label: 'Pending Review' },
    rejected: { variant: 'red',   label: 'Rejected' },
  };
  const { variant, label } = map[status] || map.approved;
  return <Badge variant={variant === 'red' ? 'coral' : variant}>{label}</Badge>;
}

/* ══════════════════════════════════════════
   LOGIN MODAL
══════════════════════════════════════════ */
function LoginModal({ onClose, onSuccess }) {
  const { login } = useAuth();
  const [email, setEmail]     = useState('');
  const [password, setPassword] = useState('');
  const [error, setError]     = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(''); setLoading(true);
    try {
      const user = login(email, password);
      toast(`Welcome back, ${user.name}!`);
      onSuccess?.(user);
      onClose();
    } catch (err) {
      setError(err.message);
    }
    setLoading(false);
  }

  return (
    <Modal title="Sign in to hate2action" onClose={onClose}
      footer={<><Button variant="ghost" onClick={onClose}>Cancel</Button><Button type="submit" onClick={handleSubmit} disabled={loading}>{loading ? 'Signing in…' : 'Sign in'}</Button></>}>
      <form onSubmit={handleSubmit}>
        {error && <div className="mb-4 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{error}</div>}
        <FormGroup label="Email"><Input type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="you@example.com" /></FormGroup>
        <FormGroup label="Password"><Input type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="••••••••" /></FormGroup>
        <div className="mt-2 p-3 rounded-lg text-xs" style={{ background: '#f0f9ff', border: '1px solid #bae6fd', color: '#0369a1' }}>
          <strong>Demo accounts:</strong><br />
          👤 user@h2a.com / user123 &nbsp;·&nbsp; 🛠 dev@h2a.com / dev123
        </div>
      </form>
    </Modal>
  );
}

/* ══════════════════════════════════════════
   REQUIRE AUTH WRAPPER
══════════════════════════════════════════ */
function RequireAuth({ children, minRole = 'user', onLogin }) {
  const { role } = useAuth();
  const roles = ['guest', 'user', 'developer'];
  if (roles.indexOf(role) >= roles.indexOf(minRole)) return children;
  return (
    <div className="max-w-md mx-auto px-6 py-16 text-center">
      <div className="text-5xl mb-4">🔐</div>
      <h2 className="text-xl font-extrabold text-charcoal mb-2">Sign in required</h2>
      <p className="text-sm text-muted mb-6">You need to be signed in to access this page.</p>
      <Button onClick={onLogin}>Sign in</Button>
    </div>
  );
}

/* ══════════════════════════════════════════
   HOME PAGE
══════════════════════════════════════════ */
function HomePage({ navigate }) {
  const { role, isDev, isUser } = useAuth();
  const orgs     = useData(() => window.api.getOrganizations());
  const projects = useData(() => window.api.getProjects());
  const problems = useData(() => window.api.getProblems());
  const messages = useData(() => window.api.getMessages());

  const cards = [
    { page: 'organizations',   icon: '🏢', title: 'Organizations', desc: 'Partner groups & NGOs',          always: true },
    { page: 'projects',        icon: '📋', title: 'Projects',       desc: 'Browse active initiatives',      always: true },
    { page: 'process-message', icon: '💬', title: 'Process Message',desc: 'Analyze a message with AI',      always: true },
    { page: 'problems',        icon: '⚠️', title: 'Problems',       desc: 'Identified social issues',       dev: true },
    { page: 'solutions',       icon: '💡', title: 'Solutions',      desc: 'Proposed approaches',            dev: true },
    { page: 'messages',        icon: '📨', title: 'Messages',       desc: 'Message history & replies',      dev: true },
    { page: 'review-queue',    icon: '📥', title: 'Review Queue',   desc: 'Approve or reject submissions',  dev: true },
    { page: 'my-submissions',  icon: '📤', title: 'My Submissions', desc: 'Track your submitted content',   user: true },
  ].filter(c => c.always || (c.dev && isDev) || (c.user && isUser && !isDev));

  return (
    <div className="max-w-5xl mx-auto px-6 py-10">
      <div className="text-center mb-10">
        <h1 className="text-4xl font-extrabold text-charcoal mb-3">Hate <span style={{color:'#E76F51'}}>to</span> Action</h1>
        <p className="text-base text-muted max-w-2xl mx-auto leading-relaxed">
          A system that turns complaints into action — connecting people with NGOs and projects already solving the problems they care about.
        </p>
        {role === 'guest' && (
          <div className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm" style={{ background: 'rgba(231,111,81,0.1)', color: '#E76F51', border: '1px solid rgba(231,111,81,0.25)' }}>
            <span>🔓</span> Sign in to submit Organizations &amp; Projects
          </div>
        )}
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 mb-10">
        {cards.map(c => (
          <Card key={c.page} onClick={() => navigate(c.page)} className="p-5 group">
            <div className="text-3xl mb-3">{c.icon}</div>
            <div className="font-bold text-charcoal text-base group-hover:text-coral transition-colors">{c.title}</div>
            <div className="text-sm text-muted mt-0.5">{c.desc}</div>
          </Card>
        ))}
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard label="Organizations" value={orgs.data?.length    ?? '—'} icon="🏢" color="navy"  />
        <StatCard label="Projects"      value={projects.data?.length ?? '—'} icon="📋" color="coral" />
        {isDev && <StatCard label="Problems" value={problems.data?.length ?? '—'} icon="⚠️" color="teal"  />}
        {isDev && <StatCard label="Messages" value={messages.data?.length ?? '—'} icon="💬" color="sage"  />}
      </div>
    </div>
  );
}

/* ══════════════════════════════════════════
   ORGANIZATIONS
══════════════════════════════════════════ */
function OrganizationsPage({ navigate, submissions, onLoginRequired }) {
  const { isDev, isUser, user } = useAuth();
  const { data: orgs, loading, error, reload } = useData(() => window.api.getOrganizations());
  const [search, setSearch] = useState('');

  // Combine API orgs + approved submissions
  const approvedSubs = submissions.filter(s => s.type === 'organization' && (s.status === 'approved' || isDev));
  const allOrgs = [...(orgs || []), ...approvedSubs.filter(s => !orgs?.find(o => o._subId === s.id))
    .map(s => ({ ...s.data, organization_id: `sub_${s.id}`, _subId: s.id, _status: s.status }))];

  const filtered = allOrgs.filter(o =>
    o.name.toLowerCase().includes(search.toLowerCase()) ||
    (o.description || '').toLowerCase().includes(search.toLowerCase())
  );

  function handleAddClick() {
    if (!isUser) { onLoginRequired(); return; }
    navigate('org-new');
  }

  return (
    <div className="max-w-5xl mx-auto px-6 py-8">
      <PageHeader title="Organizations" subtitle={allOrgs.length ? `${allOrgs.length} NGOs and partner groups` : ''}
        action={<Button onClick={handleAddClick}>+ Add Organization</Button>} />
      {error && <ApiErrorBanner error={error} onRetry={reload} />}
      <SearchBar value={search} onChange={e => setSearch(e.target.value)} placeholder="Search organizations…" />
      {loading ? <Spinner /> : filtered.length === 0 ? <EmptyState icon="🏢" title="No organizations found" /> : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filtered.map(org => (
            <Card key={org.organization_id} onClick={() => navigate('org-detail', { id: org.organization_id })} className="p-5">
              <div className="flex items-start justify-between gap-2 mb-1">
                <div className="font-bold text-charcoal leading-snug">{org.name}</div>
                {org._status && org._status !== 'approved' && <StatusBadge status={org._status} />}
              </div>
              <div className="text-sm text-muted line-clamp-2 mb-4">{org.description}</div>
              <div className="flex items-center gap-3">
                {org.website && <a href={org.website} target="_blank" rel="noopener" className="text-xs text-teal hover:underline" onClick={e=>e.stopPropagation()}>🌐 Website</a>}
                {org.contact_email && <span className="text-xs text-muted">✉ {org.contact_email.split('@')[0]}@…</span>}
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

function OrgDetailPage({ id, navigate }) {
  const { isDev } = useAuth();
  const { data: org, loading, error, reload } = useData(() =>
    String(id).startsWith('sub_') ? Promise.resolve(null) : window.api.getOrganization(id)
  );
  const [showEdit, setShowEdit] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  async function handleEdit(form) {
    try { await window.api.updateOrganization(id, form); reload(); setShowEdit(false); toast('Saved'); }
    catch (e) { toast.error(e.message); }
  }
  async function handleDelete() {
    try { await window.api.deleteOrganization(id); toast('Deleted'); navigate('organizations'); }
    catch (e) { toast.error(e.message); }
  }

  if (loading) return <div className="max-w-3xl mx-auto px-6 py-8"><BackButton onClick={() => navigate('organizations')} label="Organizations" /><Spinner /></div>;
  if (error || !org) return <div className="max-w-3xl mx-auto px-6 py-8"><BackButton onClick={() => navigate('organizations')} label="Organizations" /><ApiErrorBanner error={error || 'Not found'} onRetry={reload} /></div>;

  return (
    <div className="max-w-3xl mx-auto px-6 py-8">
      <BackButton onClick={() => navigate('organizations')} label="Organizations" />
      <div className="flex items-start justify-between mb-6">
        <h1 className="text-2xl font-extrabold text-charcoal">{org.name}</h1>
        {isDev && <div className="flex gap-2">
          <Button variant="ghost" size="sm" onClick={() => setShowEdit(true)}>Edit</Button>
          <Button variant="danger" size="sm" onClick={() => setConfirmDelete(true)}>Delete</Button>
        </div>}
      </div>
      <Card className="mb-6"><CardContent className="pt-5">
        {org.description    && <DetailRow label="Description">{org.description}</DetailRow>}
        {org.website        && <DetailRow label="Website"><a href={org.website} target="_blank" rel="noopener" className="text-teal hover:underline">{org.website}</a></DetailRow>}
        {org.contact_email  && <DetailRow label="Contact Email">{org.contact_email}</DetailRow>}
      </CardContent></Card>
      <h2 className="text-lg font-bold text-charcoal mb-3">Projects <Badge variant="navy">{(org.projects||[]).length}</Badge></h2>
      {(org.projects||[]).length === 0 ? <p className="text-sm text-muted">No projects linked.</p> :
        <div className="grid gap-3 md:grid-cols-2">{(org.projects||[]).map(p => (
          <Card key={p.project_id} onClick={() => navigate('project-detail', {id: p.project_id})} className="p-4">
            <div className="font-semibold text-sm text-charcoal">{p.name}</div>
            <div className="text-xs text-muted mt-1 line-clamp-2">{p.description}</div>
          </Card>
        ))}</div>}
      {showEdit && <OrgFormModal org={org} mode="edit" onSave={handleEdit} onClose={() => setShowEdit(false)} />}
      {confirmDelete && <ConfirmDialog message={`Delete "${org.name}"?`} onConfirm={handleDelete} onCancel={() => setConfirmDelete(false)} />}
    </div>
  );
}

/* ── Org submission form (new) ── */
function OrgNewPage({ navigate, onSubmit }) {
  const { user } = useAuth();
  const [saving, setSaving] = useState(false);
  async function handleSave(form) {
    setSaving(true);
    try { await onSubmit('organization', form, user); toast.info('Submitted for review! We\'ll notify you when it\'s approved.'); navigate('my-submissions'); }
    catch (e) { toast.error(e.message); }
    setSaving(false);
  }
  return (
    <div className="max-w-xl mx-auto px-6 py-8">
      <BackButton onClick={() => navigate('organizations')} label="Organizations" />
      <PageHeader title="Add Organization" subtitle="Your submission will be reviewed before publishing" />
      <div className="mb-4 p-3 rounded-lg text-sm" style={{ background: 'rgba(31,163,154,0.08)', border: '1px solid rgba(31,163,154,0.2)', color: '#177a73' }}>
        📋 Submissions go into <strong>Pending Review</strong> — a developer will approve or reject within 24–48h.
      </div>
      <OrgFormModal mode="submit" onSave={handleSave} onClose={() => navigate('organizations')} inline saving={saving} />
    </div>
  );
}

function OrgFormModal({ org, mode = 'edit', onSave, onClose, inline, saving }) {
  const [form, setForm] = useState({ name: org?.name||'', description: org?.description||'', website: org?.website||'', contact_email: org?.contact_email||'' });
  const set = (k,v) => setForm(f => ({...f,[k]:v}));
  const label = mode === 'submit' ? 'Submit for Review' : (org ? 'Save' : 'Add');
  const fields = (
    <>
      <FormGroup label="Name" required><Input value={form.name} onChange={e=>set('name',e.target.value)} placeholder="Organization name" /></FormGroup>
      <FormGroup label="Description"><Textarea value={form.description} onChange={e=>set('description',e.target.value)} placeholder="What does this organization do?" rows={3} /></FormGroup>
      <FormGroup label="Website"><Input value={form.website} onChange={e=>set('website',e.target.value)} placeholder="https://example.org" /></FormGroup>
      <FormGroup label="Contact Email"><Input value={form.contact_email} onChange={e=>set('contact_email',e.target.value)} placeholder="contact@example.org" /></FormGroup>
    </>
  );
  if (inline) return (
    <Card className="p-6">
      {fields}
      <div className="flex justify-end gap-3 mt-2">
        <Button variant="ghost" onClick={onClose}>Cancel</Button>
        <Button onClick={() => form.name.trim() && onSave(form)} disabled={!form.name.trim() || saving}>{saving ? 'Submitting…' : label}</Button>
      </div>
    </Card>
  );
  return (
    <Modal title={org ? 'Edit Organization' : 'New Organization'} onClose={onClose}
      footer={<><Button variant="ghost" onClick={onClose}>Cancel</Button><Button onClick={() => form.name.trim() && onSave(form)} disabled={!form.name.trim() || saving}>{saving ? 'Submitting…' : label}</Button></>}>
      {fields}
    </Modal>
  );
}

/* ══════════════════════════════════════════
   PROJECTS
══════════════════════════════════════════ */
function ProjectsPage({ navigate, submissions, onLoginRequired }) {
  const { isDev, isUser } = useAuth();
  const { data: projects, loading, error, reload } = useData(() => window.api.getProjects());
  const { data: orgs } = useData(() => window.api.getOrganizations());
  const [search, setSearch] = useState('');
  const [filterOrg, setFilterOrg] = useState('');
  const orgMap = Object.fromEntries((orgs||[]).map(o=>[o.organization_id, o.name]));

  const approvedSubs = submissions.filter(s => s.type === 'project' && (s.status === 'approved' || isDev));
  const allProjects = [...(projects||[]), ...approvedSubs.map(s => ({...s.data, project_id:`sub_${s.id}`, _status: s.status}))];

  const filtered = allProjects.filter(p => {
    const q = search.toLowerCase();
    return (p.name.toLowerCase().includes(q)||(p.description||'').toLowerCase().includes(q))
      && (!filterOrg || p.organization_id === Number(filterOrg));
  });

  function handleAddClick() {
    if (!isUser) { onLoginRequired(); return; }
    navigate('project-new');
  }

  return (
    <div className="max-w-5xl mx-auto px-6 py-8">
      <PageHeader title="Projects" subtitle={allProjects.length ? `${allProjects.length} initiatives` : ''}
        action={<Button onClick={handleAddClick}>+ Add Project</Button>} />
      {error && <ApiErrorBanner error={error} onRetry={reload} />}
      <div className="flex gap-3 mb-5">
        <div className="flex-1"><SearchBar value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search projects…" /></div>
        <Select value={filterOrg} onChange={e=>setFilterOrg(e.target.value)} className="w-52 mb-5">
          <option value="">All organizations</option>
          {(orgs||[]).map(o=><option key={o.organization_id} value={o.organization_id}>{o.name}</option>)}
        </Select>
      </div>
      {loading ? <Spinner /> : filtered.length === 0 ? <EmptyState icon="📋" title="No projects found" /> : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filtered.map(p => (
            <Card key={p.project_id} onClick={() => navigate('project-detail',{id:p.project_id})} className="p-5">
              <div className="flex items-start justify-between gap-2 mb-1">
                <div className="font-bold text-charcoal leading-snug">{p.name}</div>
                {p._status && p._status !== 'approved' && <StatusBadge status={p._status} />}
              </div>
              <div className="text-sm text-muted line-clamp-2 mb-4">{p.description}</div>
              {orgMap[p.organization_id] && <Badge variant="teal">{orgMap[p.organization_id]}</Badge>}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

function ProjectDetailPage({ id, navigate }) {
  const { isDev } = useAuth();
  const { data: project, loading, error, reload } = useData(() =>
    String(id).startsWith('sub_') ? Promise.resolve(null) : window.api.getProject(id)
  );
  const { data: orgs } = useData(() => window.api.getOrganizations());
  const [showEdit, setShowEdit] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const org = (orgs||[]).find(o=>o.organization_id===project?.organization_id);

  async function handleEdit(form) {
    try { await window.api.updateProject(id,form); reload(); setShowEdit(false); toast('Saved'); }
    catch (e) { toast.error(e.message); }
  }
  async function handleDelete() {
    try { await window.api.deleteProject(id); toast('Deleted'); navigate('projects'); }
    catch (e) { toast.error(e.message); }
  }

  if (loading) return <div className="max-w-3xl mx-auto px-6 py-8"><BackButton onClick={()=>navigate('projects')} label="Projects"/><Spinner /></div>;
  if (error||!project) return <div className="max-w-3xl mx-auto px-6 py-8"><BackButton onClick={()=>navigate('projects')} label="Projects"/><ApiErrorBanner error={error||'Not found'} onRetry={reload}/></div>;

  return (
    <div className="max-w-3xl mx-auto px-6 py-8">
      <BackButton onClick={()=>navigate('projects')} label="Projects" />
      <div className="flex items-start justify-between mb-6">
        <h1 className="text-2xl font-extrabold text-charcoal">{project.name}</h1>
        {isDev && <div className="flex gap-2">
          <Button variant="ghost" size="sm" onClick={()=>setShowEdit(true)}>Edit</Button>
          <Button variant="danger" size="sm" onClick={()=>setConfirmDelete(true)}>Delete</Button>
        </div>}
      </div>
      <Card><CardContent className="pt-5">
        {project.description   && <DetailRow label="Description">{project.description}</DetailRow>}
        {project.website       && <DetailRow label="Website"><a href={project.website} target="_blank" rel="noopener" className="text-teal hover:underline">{project.website}</a></DetailRow>}
        {project.contact_email && <DetailRow label="Email">{project.contact_email}</DetailRow>}
        {org && <DetailRow label="Organization"><button className="text-teal hover:underline font-medium" onClick={()=>navigate('org-detail',{id:org.organization_id})}>{org.name}</button></DetailRow>}
        {project.created_at    && <DetailRow label="Created">{new Date(project.created_at).toLocaleDateString()}</DetailRow>}
      </CardContent></Card>
      {showEdit && <ProjectFormModal project={project} orgs={orgs||[]} onSave={handleEdit} onClose={()=>setShowEdit(false)} />}
      {confirmDelete && <ConfirmDialog message={`Delete "${project.name}"?`} onConfirm={handleDelete} onCancel={()=>setConfirmDelete(false)} />}
    </div>
  );
}

function ProjectNewPage({ navigate, onSubmit }) {
  const { user } = useAuth();
  const { data: orgs } = useData(() => window.api.getOrganizations());
  const [saving, setSaving] = useState(false);
  async function handleSave(form) {
    setSaving(true);
    try { await onSubmit('project', form, user); toast.info('Submitted for review!'); navigate('my-submissions'); }
    catch (e) { toast.error(e.message); }
    setSaving(false);
  }
  return (
    <div className="max-w-xl mx-auto px-6 py-8">
      <BackButton onClick={()=>navigate('projects')} label="Projects" />
      <PageHeader title="Add Project" subtitle="Your submission will be reviewed before publishing" />
      <div className="mb-4 p-3 rounded-lg text-sm" style={{background:'rgba(31,163,154,0.08)',border:'1px solid rgba(31,163,154,0.2)',color:'#177a73'}}>
        📋 Submissions go into <strong>Pending Review</strong> — a developer will approve or reject within 24–48h.
      </div>
      <Card className="p-6">
        <ProjectFormModal project={null} orgs={orgs||[]} mode="submit" onSave={handleSave} onClose={()=>navigate('projects')} inline saving={saving} />
      </Card>
    </div>
  );
}

function ProjectFormModal({ project, orgs, mode='edit', onSave, onClose, inline, saving }) {
  const [form, setForm] = useState({ name:project?.name||'', description:project?.description||'', website:project?.website||'', contact_email:project?.contact_email||'', organization_id:project?.organization_id||(orgs[0]?.organization_id||'') });
  const set = (k,v) => setForm(f=>({...f,[k]:v}));
  const label = mode==='submit' ? 'Submit for Review' : (project?'Save':'Add');
  const fields = (
    <>
      <FormGroup label="Name" required><Input value={form.name} onChange={e=>set('name',e.target.value)} placeholder="Project name" /></FormGroup>
      <FormGroup label="Organization"><Select value={form.organization_id} onChange={e=>set('organization_id',e.target.value)}>
        <option value="">— none —</option>
        {orgs.map(o=><option key={o.organization_id} value={o.organization_id}>{o.name}</option>)}
      </Select></FormGroup>
      <FormGroup label="Description"><Textarea value={form.description} onChange={e=>set('description',e.target.value)} placeholder="What does this project do?" rows={3} /></FormGroup>
      <FormGroup label="Website"><Input value={form.website} onChange={e=>set('website',e.target.value)} placeholder="https://example.org" /></FormGroup>
      <FormGroup label="Contact Email"><Input value={form.contact_email} onChange={e=>set('contact_email',e.target.value)} placeholder="contact@example.org" /></FormGroup>
    </>
  );
  if (inline) return <>{fields}<div className="flex justify-end gap-3 mt-2"><Button variant="ghost" onClick={onClose}>Cancel</Button><Button onClick={()=>form.name.trim()&&onSave({...form,organization_id:Number(form.organization_id)||null})} disabled={!form.name.trim()||saving}>{saving?'Submitting…':label}</Button></div></>;
  return (
    <Modal title={project?'Edit Project':'New Project'} onClose={onClose}
      footer={<><Button variant="ghost" onClick={onClose}>Cancel</Button><Button onClick={()=>form.name.trim()&&onSave({...form,organization_id:Number(form.organization_id)||null})} disabled={!form.name.trim()||saving}>{saving?'Submitting…':label}</Button></>}>
      {fields}
    </Modal>
  );
}

/* ══════════════════════════════════════════
   PROBLEMS (developer only)
══════════════════════════════════════════ */
function ProblemsPage({ navigate }) {
  const { data: problems, loading, error, reload, setData } = useData(() => window.api.getProblems());
  const [search, setSearch] = useState('');
  const [showForm, setShowForm] = useState(false);
  async function handleAdd(form) {
    try { const c=await window.api.createProblem(form); setData(p=>[...(p||[]),c]); setShowForm(false); toast('Problem added'); }
    catch(e) { toast.error(e.message); }
  }
  const filtered = (problems||[]).filter(p=>p.name.toLowerCase().includes(search.toLowerCase())||(p.context||'').toLowerCase().includes(search.toLowerCase()));
  return (
    <div className="max-w-5xl mx-auto px-6 py-8">
      <PageHeader title="Problems" subtitle="AI-extracted social issues" action={<Button onClick={()=>setShowForm(true)}>+ New Problem</Button>} />
      {error && <ApiErrorBanner error={error} onRetry={reload} />}
      <SearchBar value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search problems…" />
      {loading ? <Spinner /> : filtered.length===0 ? <EmptyState icon="⚠️" title="No problems found" /> : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filtered.map(p=>(
            <Card key={p.problem_id} onClick={()=>navigate('problem-detail',{id:p.problem_id})} className="p-5">
              <div className="flex items-start justify-between gap-2 mb-2">
                <div className="font-bold text-charcoal leading-snug">{p.name}</div>
                <Badge variant={p.is_processed?'teal':'coral'}>{p.is_processed?'Done':'Pending'}</Badge>
              </div>
              <div className="text-sm text-muted line-clamp-2">{p.context}</div>
            </Card>
          ))}
        </div>
      )}
      {showForm && <ProblemFormModal onSave={handleAdd} onClose={()=>setShowForm(false)} />}
    </div>
  );
}
function ProblemDetailPage({ id, navigate }) {
  const { data: problem, loading, error, reload } = useData(()=>window.api.getProblem(id));
  const [showEdit, setShowEdit] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  async function handleEdit(form) { try { await window.api.updateProblem(id,form); reload(); setShowEdit(false); toast('Saved'); } catch(e){toast.error(e.message);} }
  async function handleDelete() { try { await window.api.deleteProblem(id); toast('Deleted'); navigate('problems'); } catch(e){toast.error(e.message);} }
  if (loading) return <div className="max-w-3xl mx-auto px-6 py-8"><BackButton onClick={()=>navigate('problems')} label="Problems"/><Spinner /></div>;
  if (error||!problem) return <div className="max-w-3xl mx-auto px-6 py-8"><BackButton onClick={()=>navigate('problems')} label="Problems"/><ApiErrorBanner error={error||'Not found'} onRetry={reload}/></div>;
  return (
    <div className="max-w-3xl mx-auto px-6 py-8">
      <BackButton onClick={()=>navigate('problems')} label="Problems" />
      <div className="flex items-start justify-between mb-6">
        <h1 className="text-2xl font-extrabold text-charcoal">{problem.name}</h1>
        <div className="flex gap-2 items-center">
          <Badge variant={problem.is_processed?'teal':'coral'}>{problem.is_processed?'Processed':'Pending'}</Badge>
          <Button variant="ghost" size="sm" onClick={()=>setShowEdit(true)}>Edit</Button>
          <Button variant="danger" size="sm" onClick={()=>setConfirmDelete(true)}>Delete</Button>
        </div>
      </div>
      <Card><CardContent className="pt-5">
        {problem.context && <DetailRow label="Context">{problem.context}</DetailRow>}
        {problem.content && <DetailRow label="Content">{problem.content}</DetailRow>}
        {problem.created_at && <DetailRow label="Created">{new Date(problem.created_at).toLocaleDateString()}</DetailRow>}
      </CardContent></Card>
      {showEdit && <ProblemFormModal problem={problem} onSave={handleEdit} onClose={()=>setShowEdit(false)} />}
      {confirmDelete && <ConfirmDialog message={`Delete "${problem.name}"?`} onConfirm={handleDelete} onCancel={()=>setConfirmDelete(false)} />}
    </div>
  );
}
function ProblemFormModal({ problem, onSave, onClose }) {
  const [form, setForm] = useState({name:problem?.name||'',context:problem?.context||'',is_processed:problem?.is_processed||0});
  const set=(k,v)=>setForm(f=>({...f,[k]:v}));
  return (
    <Modal title={problem?'Edit Problem':'New Problem'} onClose={onClose}
      footer={<><Button variant="ghost" onClick={onClose}>Cancel</Button><Button onClick={()=>form.name.trim()&&onSave(form)} disabled={!form.name.trim()}>{problem?'Save':'Add'}</Button></>}>
      <FormGroup label="Name" required><Input value={form.name} onChange={e=>set('name',e.target.value)} placeholder="Problem name" /></FormGroup>
      <FormGroup label="Context"><Textarea value={form.context} onChange={e=>set('context',e.target.value)} placeholder="Short context" rows={3} /></FormGroup>
      {problem && <FormGroup label="Status"><Select value={form.is_processed} onChange={e=>set('is_processed',Number(e.target.value))}><option value={0}>Pending</option><option value={1}>Processed</option></Select></FormGroup>}
    </Modal>
  );
}

/* ══════════════════════════════════════════
   SOLUTIONS (developer only)
══════════════════════════════════════════ */
function SolutionsPage({ navigate }) {
  const { data: solutions, loading, error, reload, setData } = useData(()=>window.api.getSolutions());
  const [search, setSearch] = useState('');
  const [showForm, setShowForm] = useState(false);
  async function handleAdd(form) { try { const c=await window.api.createSolution(form); setData(s=>[...(s||[]),c]); setShowForm(false); toast('Added'); } catch(e){toast.error(e.message);} }
  const filtered = (solutions||[]).filter(s=>s.name.toLowerCase().includes(search.toLowerCase())||(s.context||'').toLowerCase().includes(search.toLowerCase()));
  return (
    <div className="max-w-5xl mx-auto px-6 py-8">
      <PageHeader title="Solutions" subtitle="Proposed approaches" action={<Button onClick={()=>setShowForm(true)}>+ New Solution</Button>} />
      {error && <ApiErrorBanner error={error} onRetry={reload} />}
      <SearchBar value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search solutions…" />
      {loading ? <Spinner /> : filtered.length===0 ? <EmptyState icon="💡" title="No solutions found" /> : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filtered.map(s=>(
            <Card key={s.solution_id} onClick={()=>navigate('solution-detail',{id:s.solution_id})} className="p-5">
              <div className="font-bold text-charcoal mb-1 leading-snug">💡 {s.name}</div>
              <div className="text-sm text-muted line-clamp-2">{s.context}</div>
            </Card>
          ))}
        </div>
      )}
      {showForm && <SolutionFormModal onSave={handleAdd} onClose={()=>setShowForm(false)} />}
    </div>
  );
}
function SolutionDetailPage({ id, navigate }) {
  const { data: s, loading, error, reload } = useData(()=>window.api.getSolution(id));
  const [showEdit, setShowEdit] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  async function handleEdit(form) { try { await window.api.updateSolution(id,form); reload(); setShowEdit(false); toast('Saved'); } catch(e){toast.error(e.message);} }
  async function handleDelete() { try { await window.api.deleteSolution(id); toast('Deleted'); navigate('solutions'); } catch(e){toast.error(e.message);} }
  if (loading) return <div className="max-w-3xl mx-auto px-6 py-8"><BackButton onClick={()=>navigate('solutions')} label="Solutions"/><Spinner /></div>;
  if (error||!s) return <div className="max-w-3xl mx-auto px-6 py-8"><BackButton onClick={()=>navigate('solutions')} label="Solutions"/><ApiErrorBanner error={error||'Not found'} onRetry={reload}/></div>;
  return (
    <div className="max-w-3xl mx-auto px-6 py-8">
      <BackButton onClick={()=>navigate('solutions')} label="Solutions" />
      <div className="flex items-start justify-between mb-6">
        <h1 className="text-2xl font-extrabold text-charcoal">{s.name}</h1>
        <div className="flex gap-2"><Button variant="ghost" size="sm" onClick={()=>setShowEdit(true)}>Edit</Button><Button variant="danger" size="sm" onClick={()=>setConfirmDelete(true)}>Delete</Button></div>
      </div>
      <Card><CardContent className="pt-5">
        {s.context && <DetailRow label="Context">{s.context}</DetailRow>}
        {s.content && <DetailRow label="Content">{s.content}</DetailRow>}
        {s.created_at && <DetailRow label="Created">{new Date(s.created_at).toLocaleDateString()}</DetailRow>}
      </CardContent></Card>
      {showEdit && <SolutionFormModal solution={s} onSave={handleEdit} onClose={()=>setShowEdit(false)} />}
      {confirmDelete && <ConfirmDialog message={`Delete "${s.name}"?`} onConfirm={handleDelete} onCancel={()=>setConfirmDelete(false)} />}
    </div>
  );
}
function SolutionFormModal({ solution, onSave, onClose }) {
  const [form, setForm] = useState({name:solution?.name||'',context:solution?.context||''});
  const set=(k,v)=>setForm(f=>({...f,[k]:v}));
  return (
    <Modal title={solution?'Edit Solution':'New Solution'} onClose={onClose}
      footer={<><Button variant="ghost" onClick={onClose}>Cancel</Button><Button onClick={()=>form.name.trim()&&onSave(form)} disabled={!form.name.trim()}>{solution?'Save':'Add'}</Button></>}>
      <FormGroup label="Name" required><Input value={form.name} onChange={e=>set('name',e.target.value)} placeholder="Solution name" /></FormGroup>
      <FormGroup label="Context"><Textarea value={form.context} onChange={e=>set('context',e.target.value)} placeholder="Short description" rows={3} /></FormGroup>
    </Modal>
  );
}

/* ══════════════════════════════════════════
   PROCESS MESSAGE
══════════════════════════════════════════ */
function ProcessMessagePage({ navigate }) {
  const [text, setText] = useState('');
  const [style, setStyle] = useState('normal');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const STYLES = ['normal','polite','funny','sarcastic','rude'];

  async function handleSubmit() {
    if (!text.trim()||loading) return;
    setLoading(true); setResult(null);
    try { const res=await window.api.processMessage(text,style); setResult({ok:true,data:res,text}); toast.info('Processed'); }
    catch(e) { setResult({ok:false,error:e.message}); toast.error(e.message); }
    setLoading(false);
  }

  return (
    <div className="max-w-2xl mx-auto px-6 py-8">
      <PageHeader title="Process Message" subtitle="Run the AI pipeline on any user message" />
      <Card className="p-6 mb-5">
        <FormGroup label="Message Text" required>
          <Textarea value={text} onChange={e=>setText(e.target.value)} placeholder="Paste a complaint or rant here…" rows={5} />
        </FormGroup>
        <FormGroup label="Response Style">
          <div className="flex flex-wrap gap-2 mt-1">
            {STYLES.map(s=>(
              <button key={s} onClick={()=>setStyle(s)} className={`px-3 py-1.5 rounded-full text-xs font-semibold border transition-all ${style===s?'bg-coral text-white border-coral':'bg-white text-muted border-border hover:border-coral/50'}`}>
                {s.charAt(0).toUpperCase()+s.slice(1)}
              </button>
            ))}
          </div>
        </FormGroup>
        <Button onClick={handleSubmit} disabled={!text.trim()||loading}>{loading?'⏳ Processing…':'▶ Process Message'}</Button>
      </Card>
      {result?.ok && (
        <Card className="p-6">
          <div className="bg-sand rounded-lg p-4 mb-4"><p className="text-xs font-bold text-muted uppercase tracking-wider mb-1">User Message</p><p className="text-sm text-charcoal">{result.text}</p></div>
          <div className="mb-4"><p className="text-xs font-bold text-muted uppercase tracking-wider mb-1">Bot Reply</p><div className="text-sm text-charcoal whitespace-pre-wrap leading-relaxed bg-white border border-border rounded-lg p-4">{result.data.text}</div></div>
          {result.data.problems?.length>0 && <div className="mb-3"><p className="text-xs font-bold text-muted uppercase tracking-wider mb-1.5">Problems</p><div className="flex flex-wrap gap-2">{result.data.problems.map(p=><Badge key={p.problem_id} variant="coral">{p.name}</Badge>)}</div></div>}
          {result.data.solutions?.length>0 && <div className="mb-3"><p className="text-xs font-bold text-muted uppercase tracking-wider mb-1.5">Solutions</p><div className="flex flex-wrap gap-2">{result.data.solutions.map(s=><Badge key={s.solution_id} variant="teal">{s.name}</Badge>)}</div></div>}
          {result.data.projects?.length>0  && <div><p className="text-xs font-bold text-muted uppercase tracking-wider mb-1.5">Projects</p><div className="flex flex-wrap gap-2">{result.data.projects.map(p=><Badge key={p.project_id} variant="navy">{p.name}</Badge>)}</div></div>}
        </Card>
      )}
      {result?.ok===false && <ApiErrorBanner error={result.error} />}
    </div>
  );
}

/* ══════════════════════════════════════════
   MESSAGES (developer only)
══════════════════════════════════════════ */
function MessagesPage({ navigate }) {
  const { data: messages, loading, error, reload } = useData(()=>window.api.getMessages());
  const [search, setSearch] = useState('');
  const filtered = (messages||[]).filter(m=>(m.text||'').toLowerCase().includes(search.toLowerCase())||(m.user_username||'').toLowerCase().includes(search.toLowerCase()));
  return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      <PageHeader title="Messages" subtitle={messages?`${messages.length} processed messages`:''} />
      {error && <ApiErrorBanner error={error} onRetry={reload} />}
      <SearchBar value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search messages…" />
      {loading ? <Spinner /> : filtered.length===0
        ? <EmptyState icon="📨" title="No messages" action={<Button onClick={()=>navigate('process-message')}>Process a message</Button>} />
        : <div className="flex flex-col gap-3">{filtered.map(msg=>(
            <Card key={msg.message_id} onClick={()=>navigate('message-detail',{id:msg.message_id})} className="p-5">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                    <span className="font-bold text-sm text-charcoal">@{msg.user_username}</span>
                    {msg.chat_title && <span className="text-xs text-muted">{msg.chat_title}</span>}
                  </div>
                  <p className="text-sm text-charcoal line-clamp-2">{msg.text}</p>
                  {msg.response?.text && <p className="text-xs text-muted mt-1 line-clamp-1 italic">↳ {msg.response.text.replace(/\*\*/g,'').substring(0,80)}…</p>}
                </div>
              </div>
            </Card>
          ))}</div>
      }
    </div>
  );
}
function MessageDetailPage({ id, navigate }) {
  const { data: msg, loading, error, reload } = useData(()=>window.api.getMessage(id));
  if (loading) return <div className="max-w-3xl mx-auto px-6 py-8"><BackButton onClick={()=>navigate('messages')} label="Messages"/><Spinner /></div>;
  if (error||!msg) return <div className="max-w-3xl mx-auto px-6 py-8"><BackButton onClick={()=>navigate('messages')} label="Messages"/><ApiErrorBanner error={error||'Not found'} onRetry={reload}/></div>;
  return (
    <div className="max-w-3xl mx-auto px-6 py-8">
      <BackButton onClick={()=>navigate('messages')} label="Messages" />
      <h1 className="text-2xl font-extrabold text-charcoal mb-6">Message Details</h1>
      <Card className="mb-5"><CardHeader><CardTitle>Metadata</CardTitle></CardHeader><CardContent>
        <DetailRow label="From">@{msg.user_username}</DetailRow>
        {msg.chat_title && <DetailRow label="Chat">{msg.chat_title}</DetailRow>}
      </CardContent></Card>
      <Card className="mb-5"><CardHeader><CardTitle>User Message</CardTitle></CardHeader><CardContent><p className="text-sm text-charcoal">{msg.text}</p></CardContent></Card>
      {msg.response && (
        <Card><CardHeader><CardTitle>Bot Reply</CardTitle></CardHeader><CardContent>
          <div className="bg-sand rounded-lg p-4 text-sm text-charcoal whitespace-pre-wrap leading-relaxed mb-4">{msg.response.text}</div>
          {msg.response.problems?.length>0 && <div className="mb-3"><p className="text-xs font-bold text-muted uppercase tracking-wider mb-2">Problems</p><div className="flex flex-wrap gap-2">{msg.response.problems.map(p=><Badge key={p.problem_id} variant="coral">{p.name}</Badge>)}</div></div>}
          {msg.response.solutions?.length>0 && <div className="mb-3"><p className="text-xs font-bold text-muted uppercase tracking-wider mb-2">Solutions</p><div className="flex flex-wrap gap-2">{msg.response.solutions.map(s=><Badge key={s.solution_id} variant="teal">{s.name}</Badge>)}</div></div>}
          {msg.response.projects?.length>0  && <div><p className="text-xs font-bold text-muted uppercase tracking-wider mb-2">Projects</p><div className="flex flex-wrap gap-2">{msg.response.projects.map(p=><Badge key={p.project_id} variant="navy">{p.name}</Badge>)}</div></div>}
        </CardContent></Card>
      )}
    </div>
  );
}

/* ══════════════════════════════════════════
   MY SUBMISSIONS (logged-in users)
══════════════════════════════════════════ */
function MySubmissionsPage({ navigate, submissions, user }) {
  const mine = submissions.filter(s => s.userId === user?.id);
  const byStatus = (status) => mine.filter(s => s.status === status);
  return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      <PageHeader title="My Submissions" subtitle="Track the status of your submitted organizations and projects" />
      {mine.length === 0 ? (
        <EmptyState icon="📤" title="No submissions yet" description="Add an organization or project to get started."
          action={<div className="flex gap-3"><Button onClick={()=>navigate('org-new')}>+ Organization</Button><Button variant="ghost" onClick={()=>navigate('project-new')}>+ Project</Button></div>} />
      ) : (
        <>
          {['pending','approved','rejected'].map(status => {
            const items = byStatus(status);
            if (!items.length) return null;
            return (
              <div key={status} className="mb-8">
                <div className="flex items-center gap-3 mb-4">
                  <h2 className="text-base font-bold text-charcoal capitalize">{status}</h2>
                  <Badge variant={status==='approved'?'teal':status==='pending'?'coral':'coral'}>{items.length}</Badge>
                </div>
                <div className="flex flex-col gap-3">
                  {items.map(sub => (
                    <Card key={sub.id} className="p-5">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-xs font-bold text-muted uppercase tracking-wider">{sub.type}</span>
                            <StatusBadge status={sub.status} />
                          </div>
                          <div className="font-bold text-charcoal">{sub.data.name}</div>
                          {sub.data.description && <div className="text-sm text-muted mt-1 line-clamp-2">{sub.data.description}</div>}
                          {sub.reviewNote && (
                            <div className="mt-2 text-xs px-3 py-2 rounded-lg" style={{background:'rgba(231,111,81,0.08)',color:'#c85a3d',border:'1px solid rgba(231,111,81,0.2)'}}>
                              💬 Reviewer note: {sub.reviewNote}
                            </div>
                          )}
                        </div>
                        <div className="text-xs text-muted flex-shrink-0">{new Date(sub.submittedAt).toLocaleDateString()}</div>
                      </div>
                    </Card>
                  ))}
                </div>
              </div>
            );
          })}
        </>
      )}
    </div>
  );
}

/* ══════════════════════════════════════════
   REVIEW QUEUE (developer only)
══════════════════════════════════════════ */
function ReviewQueuePage({ submissions, onReview }) {
  const pending = submissions.filter(s => s.status === 'pending');
  const [noteModal, setNoteModal] = useState(null); // { id, action }
  const [note, setNote] = useState('');

  function handleAction(id, action, reviewNote='') {
    onReview(id, action, reviewNote);
    toast(action === 'approved' ? '✅ Approved' : '❌ Rejected');
    setNoteModal(null); setNote('');
  }

  return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      <PageHeader title="Review Queue" subtitle={`${pending.length} submission${pending.length!==1?'s':''} awaiting review`} />
      {pending.length === 0 ? (
        <EmptyState icon="🎉" title="Queue is empty" description="All submissions have been reviewed." />
      ) : (
        <div className="flex flex-col gap-4">
          {pending.map(sub => (
            <Card key={sub.id} className="p-5">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-xs font-bold text-muted uppercase tracking-wider bg-sand px-2 py-0.5 rounded">{sub.type}</span>
                    <StatusBadge status={sub.status} />
                    <span className="text-xs text-muted">by {sub.userName} · {new Date(sub.submittedAt).toLocaleDateString()}</span>
                  </div>
                  <div className="font-bold text-charcoal text-base mb-1">{sub.data.name}</div>
                  {sub.data.description && <p className="text-sm text-muted mb-2 line-clamp-2">{sub.data.description}</p>}
                  <div className="flex gap-4 flex-wrap text-xs text-muted">
                    {sub.data.website && <span>🌐 {sub.data.website}</span>}
                    {sub.data.contact_email && <span>✉ {sub.data.contact_email}</span>}
                  </div>
                </div>
                <div className="flex flex-col gap-2 flex-shrink-0">
                  <Button size="sm" variant="teal" onClick={() => handleAction(sub.id, 'approved')}>✓ Approve</Button>
                  <Button size="sm" variant="danger" onClick={() => setNoteModal({ id: sub.id, action: 'rejected' })}>✕ Reject</Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Reject with note */}
      {noteModal && (
        <Modal title="Reject Submission" onClose={() => setNoteModal(null)}
          footer={<><Button variant="ghost" onClick={()=>setNoteModal(null)}>Cancel</Button><Button variant="danger" onClick={()=>handleAction(noteModal.id,'rejected',note)}>Reject</Button></>}>
          <FormGroup label="Reason (shown to submitter)" hint="Optional but helpful">
            <Textarea value={note} onChange={e=>setNote(e.target.value)} placeholder="e.g. Duplicate entry, missing description, inappropriate content…" rows={3} />
          </FormGroup>
        </Modal>
      )}
    </div>
  );
}

/* ══════════════════════════════════════════
   BOT TEST LAB (developer only)
══════════════════════════════════════════ */
function BotTestLabPage() {
  const [tab, setTab] = useState('run'); // 'run' | 'review'
  const { data: cases, loading, error, reload, setData } = useData(() => window.api.getTestCases());

  const [filterLang,  setFilterLang]  = useState('');
  const [filterStyle, setFilterStyle] = useState('');
  const [filterTopic, setFilterTopic] = useState('');
  const [onlyUnfilled, setOnlyUnfilled] = useState(true);
  const [limit, setLimit] = useState('');

  const [running, setRunning]   = useState(false);
  const stopRef = useRef(false);
  const [progress, setProgress] = useState({ done: 0, total: 0, current: null });

  const all = cases || [];
  const langs  = [...new Set(all.map(c => c.lang))].sort();
  const styles = [...new Set(all.map(c => c.style))].sort();
  const topics = [...new Set(all.map(c => c.topic))].sort();

  const filtered = all.filter(c =>
    (!filterLang  || c.lang  === filterLang)  &&
    (!filterStyle || c.style === filterStyle) &&
    (!filterTopic || c.topic === filterTopic)
  );
  const runnable = filtered
    .filter(c => !onlyUnfilled || !(c.output || '').trim())
    .slice(0, limit ? Number(limit) : undefined);

  async function runOne(c) {
    const res    = await window.api.processMessage(c.message_input, c.style);
    const output = (res?.text || '').trim();
    await window.api.updateTestCase(c.id, { output });
    setData(prev => prev.map(x => x.id === c.id ? { ...x, output } : x));
    return output;
  }

  async function runBatch() {
    if (running) return;
    setRunning(true); stopRef.current = false;
    setProgress({ done: 0, total: runnable.length, current: null });
    for (let i = 0; i < runnable.length; i++) {
      if (stopRef.current) break;
      const c = runnable[i];
      setProgress({ done: i, total: runnable.length, current: c });
      try { await runOne(c); }
      catch (e) { toast.error(`#${c.id}: ${e.message}`); }
      setProgress({ done: i + 1, total: runnable.length, current: null });
    }
    setRunning(false);
    toast(stopRef.current ? 'Stopped' : '✅ Run complete');
  }

  function exportCsv() {
    const cols = ['id','lang','style','topic','message_input','output','comment'];
    const esc  = v => `"${String(v ?? '').replace(/"/g,'""')}"`;
    const rows = [cols.join(','), ...filtered.map(c => cols.map(k => esc(c[k])).join(','))];
    const blob = new Blob(['﻿' + rows.join('\n')], { type:'text/csv;charset=utf-8' });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href = url; a.download = 'bot_test_results.csv'; a.click();
    URL.revokeObjectURL(url);
  }

  if (loading) return <div className="max-w-6xl mx-auto px-6 py-8"><Spinner /></div>;
  if (error)   return <div className="max-w-6xl mx-auto px-6 py-8"><ApiErrorBanner error={error} onRetry={reload} /></div>;

  const filledCount = all.filter(c => (c.output || '').trim()).length;
  const commentedCount = all.filter(c => (c.comment || '').trim()).length;

  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      <PageHeader title="Bot Test Lab" subtitle={`${all.length} cases · ${filledCount} replied · ${commentedCount} commented`}
        action={<Button variant="ghost" size="sm" onClick={exportCsv}>↓ Export CSV</Button>} />

      <div className="flex gap-2 mb-6 border-b border-border">
        {[{key:'run',label:'▶ Run'},{key:'review',label:'📝 Review & Comment'}].map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className="px-4 py-2 text-sm font-semibold border-b-2 -mb-px transition-colors"
            style={{
              color: tab === t.key ? '#E76F51' : '#6B7280',
              borderColor: tab === t.key ? '#E76F51' : 'transparent'
            }}>{t.label}</button>
        ))}
      </div>

      <Card className="p-4 mb-5">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
          <div>
            <div className="text-xs font-bold text-muted mb-1">Language</div>
            <Select value={filterLang} onChange={e => setFilterLang(e.target.value)}>
              <option value="">All</option>
              {langs.map(l => <option key={l} value={l}>{l}</option>)}
            </Select>
          </div>
          <div>
            <div className="text-xs font-bold text-muted mb-1">Style</div>
            <Select value={filterStyle} onChange={e => setFilterStyle(e.target.value)}>
              <option value="">All</option>
              {styles.map(s => <option key={s} value={s}>{s}</option>)}
            </Select>
          </div>
          <div>
            <div className="text-xs font-bold text-muted mb-1">Topic</div>
            <Select value={filterTopic} onChange={e => setFilterTopic(e.target.value)}>
              <option value="">All</option>
              {topics.map(t => <option key={t} value={t}>{t.length > 32 ? t.slice(0,32)+'…' : t}</option>)}
            </Select>
          </div>
          <div>
            <div className="text-xs font-bold text-muted mb-1">Limit (per run)</div>
            <Input type="number" value={limit} onChange={e => setLimit(e.target.value)} placeholder="all" min="1" />
          </div>
        </div>
        <div className="text-sm text-muted flex items-center gap-4 flex-wrap">
          <span><strong className="text-charcoal">{filtered.length}</strong> match filters</span>
          {tab === 'run' && (
            <>
              <span>· <strong className="text-charcoal">{runnable.length}</strong> will run</span>
              <label className="inline-flex items-center gap-2 cursor-pointer">
                <input type="checkbox" checked={onlyUnfilled} onChange={e => setOnlyUnfilled(e.target.checked)} />
                <span>only unfilled</span>
              </label>
            </>
          )}
        </div>
      </Card>

      {tab === 'run'    && <RunPanel    cases={filtered} runnable={runnable} running={running} progress={progress} onRun={runBatch} onStop={() => { stopRef.current = true; }} onRunOne={runOne} />}
      {tab === 'review' && <ReviewPanel cases={filtered} setData={setData} />}
    </div>
  );
}

function RunPanel({ cases, runnable, running, progress, onRun, onStop, onRunOne }) {
  const pct = progress.total ? (progress.done / progress.total) * 100 : 0;
  return (
    <div>
      <Card className="p-5 mb-5">
        <div className="flex items-center gap-3 mb-3 flex-wrap">
          {!running
            ? <Button onClick={onRun} disabled={runnable.length === 0}>▶ Run {runnable.length} test{runnable.length !== 1 ? 's' : ''}</Button>
            : <Button variant="danger" onClick={onStop}>■ Stop</Button>}
          {running && <span className="text-sm text-muted">Running {progress.done}/{progress.total}…</span>}
        </div>
        {running && (
          <>
            <div className="w-full bg-sand rounded-full h-2 overflow-hidden">
              <div className="bg-coral h-2 transition-all" style={{ width: `${pct}%` }} />
            </div>
            {progress.current && (
              <div className="mt-2 text-xs text-muted truncate">
                ▸ #{progress.current.id} [{progress.current.lang}/{progress.current.style}] {progress.current.message_input.slice(0,100)}…
              </div>
            )}
          </>
        )}
      </Card>

      <div className="overflow-auto bg-white border border-border rounded-lg">
        <table className="w-full text-sm border-collapse">
          <thead className="bg-sand">
            <tr>
              <th className="text-left p-2 font-bold w-14">ID</th>
              <th className="text-left p-2 font-bold w-12">Lang</th>
              <th className="text-left p-2 font-bold w-20">Style</th>
              <th className="text-left p-2 font-bold">Input</th>
              <th className="text-left p-2 font-bold">Output</th>
              <th className="text-left p-2 font-bold w-20"></th>
            </tr>
          </thead>
          <tbody>
            {cases.slice(0, 200).map(c => (
              <tr key={c.id} className="border-t border-border align-top">
                <td className="p-2 font-mono text-xs">{c.id}</td>
                <td className="p-2 text-xs">{c.lang}</td>
                <td className="p-2 text-xs">{c.style}</td>
                <td className="p-2 text-xs"><div className="line-clamp-2">{c.message_input}</div></td>
                <td className="p-2 text-xs">
                  {(c.output || '').trim()
                    ? <div className="line-clamp-2">{c.output}</div>
                    : <span className="text-muted italic">— pending —</span>}
                </td>
                <td className="p-2">
                  <Button size="sm" variant="ghost" disabled={running}
                    onClick={() => onRunOne(c).catch(e => toast.error(e.message))}>
                    {(c.output || '').trim() ? 'Re-run' : 'Run'}
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {cases.length > 200 && (
          <p className="text-xs text-muted text-center py-2 border-t border-border">
            Showing first 200 of {cases.length} — narrow with filters to see more
          </p>
        )}
      </div>
    </div>
  );
}

function ReviewPanel({ cases, setData }) {
  const replied = cases.filter(c => (c.output || '').trim());
  if (replied.length === 0) return <EmptyState icon="📝" title="Nothing to review yet" description="Run some tests first." />;
  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm text-muted">{replied.length} replied case{replied.length !== 1 ? 's' : ''}</p>
      {replied.map(c => <ReviewCard key={c.id} testCase={c} setData={setData} />)}
    </div>
  );
}

function ReviewCard({ testCase: c, setData }) {
  const [comment, setComment] = useState(c.comment || '');
  const [saving, setSaving]   = useState(false);
  const [dirty, setDirty]     = useState(false);

  async function save() {
    if (!dirty || saving) return;
    setSaving(true);
    try {
      await window.api.updateTestCase(c.id, { comment });
      setData(prev => prev.map(x => x.id === c.id ? { ...x, comment } : x));
      setDirty(false);
      toast('💾 Saved');
    } catch (e) { toast.error(e.message); }
    setSaving(false);
  }

  return (
    <Card className="p-5">
      <div className="flex items-center gap-2 mb-3 flex-wrap">
        <span className="text-xs font-mono text-muted">#{c.id}</span>
        <Badge variant="navy">{c.lang}</Badge>
        <Badge variant="teal">{c.style}</Badge>
        <Badge variant="coral">{c.topic}</Badge>
        {(c.comment || '').trim() && <Badge variant="sage">commented</Badge>}
      </div>
      <div className="grid md:grid-cols-2 gap-3 mb-3">
        <div>
          <p className="text-xs font-bold text-muted uppercase tracking-wider mb-1">Input</p>
          <div className="bg-sand rounded-lg p-3 text-sm whitespace-pre-wrap">{c.message_input}</div>
        </div>
        <div>
          <p className="text-xs font-bold text-muted uppercase tracking-wider mb-1">Bot Reply</p>
          <div className="bg-white border border-border rounded-lg p-3 text-sm whitespace-pre-wrap">{c.output}</div>
        </div>
      </div>
      <div>
        <p className="text-xs font-bold text-muted uppercase tracking-wider mb-1">My Comment</p>
        <Textarea value={comment} onChange={e => { setComment(e.target.value); setDirty(true); }} onBlur={save}
          placeholder="What do you like / dislike about this reply?" rows={2} />
        <div className="flex justify-end mt-1">
          <Button size="sm" variant="ghost" onClick={save} disabled={!dirty || saving}>
            {saving ? 'Saving…' : dirty ? 'Save' : '✓ Saved'}
          </Button>
        </div>
      </div>
    </Card>
  );
}

/* ══════════════════════════════════════════
   APP ROOT
══════════════════════════════════════════ */
const GUEST_NAV = [
  { page:'organizations', label:'Organizations' },
  { page:'projects',      label:'Projects'      },
  { page:'process-message',label:'Process Message'},
];
const USER_NAV = [
  { page:'organizations', label:'Organizations' },
  { page:'projects',      label:'Projects'      },
  { page:'org-new',       label:'+ Add Org'     },
  { page:'project-new',   label:'+ Add Project' },
  { page:'my-submissions',label:'My Submissions'},
  { page:'process-message',label:'Process Message'},
];
const DEV_NAV = [
  { page:'home',           label:'Dashboard'     },
  { page:'organizations',  label:'Organizations' },
  { page:'projects',       label:'Projects'      },
  { page:'problems',       label:'Problems'      },
  { page:'solutions',      label:'Solutions'     },
  { page:'messages',       label:'Messages'      },
  { page:'review-queue',   label:'Review Queue'  },
  { page:'process-message',label:'Process Message'},
  { page:'bot-test-lab',   label:'Test Lab'      },
];

function App() {
  const { route, navigate } = useRouter();
  const [showSettings, setShowSettings] = useState(false);
  const [showLogin, setShowLogin] = useState(false);

  // Submission store (in-memory; would be API-backed in production)
  const [submissions, setSubmissions] = useState([]);

  function handleSubmit(type, data, user) {
    const sub = { id: Date.now(), type, data, status: 'pending', userId: user?.id, userName: user?.name, submittedAt: new Date().toISOString() };
    setSubmissions(prev => [...prev, sub]);
    return sub;
  }
  function handleReview(id, status, reviewNote) {
    setSubmissions(prev => prev.map(s => s.id === id ? { ...s, status, reviewNote } : s));
  }

  return (
    <AuthProvider>
      <AppInner
        route={route} navigate={navigate}
        showSettings={showSettings} setShowSettings={setShowSettings}
        showLogin={showLogin} setShowLogin={setShowLogin}
        submissions={submissions} handleSubmit={handleSubmit} handleReview={handleReview}
      />
    </AuthProvider>
  );
}

function AppInner({ route, navigate, showSettings, setShowSettings, showLogin, setShowLogin, submissions, handleSubmit, handleReview }) {
  const { user, role, isDev, isUser, isGuest, logout } = useAuth();
  const p = route.page;

  const navLinks = isDev ? DEV_NAV : isUser ? USER_NAV : GUEST_NAV;
  const pendingCount = submissions.filter(s=>s.status==='pending').length;

  function onLoginRequired() { setShowLogin(true); }

  const pageProps = { navigate, submissions, onLoginRequired };

  return (
    <div style={{ minHeight:'100vh', background:'#F4EDE4' }}>
      {/* HEADER */}
      <header style={{ background:'#1F3A5F', borderBottom:'1px solid rgba(255,255,255,0.08)', position:'sticky', top:0, zIndex:40 }}>
        <div className="max-w-6xl mx-auto px-6 flex items-center h-14 gap-6">
          <button onClick={()=>navigate('home')} className="flex items-center gap-2 font-extrabold text-white text-base hover:opacity-90 transition-opacity flex-shrink-0">
            <span style={{fontSize:18}}>🔥</span> hate<span style={{color:'#E76F51'}}>2</span>action
          </button>

          <nav className="flex items-center gap-1 flex-1 overflow-x-auto">
            {navLinks.map(link => {
              const isActive = p === link.page || (p.includes('-detail') && p.startsWith(link.page.slice(0,4)));
              return (
                <button key={link.page} onClick={()=>navigate(link.page)}
                  className="relative px-3 py-1.5 rounded-md text-sm font-medium transition-all whitespace-nowrap flex-shrink-0"
                  style={{ color:isActive?'#E76F51':'rgba(255,255,255,0.65)', background:isActive?'rgba(231,111,81,0.12)':'transparent' }}>
                  {link.label}
                  {link.page==='review-queue' && pendingCount>0 && (
                    <span style={{position:'absolute',top:2,right:2,background:'#E76F51',color:'#fff',fontSize:9,fontWeight:800,borderRadius:'999px',width:14,height:14,display:'flex',alignItems:'center',justifyContent:'center'}}>{pendingCount}</span>
                  )}
                </button>
              );
            })}
          </nav>

          <div className="flex items-center gap-2 flex-shrink-0">
            {/* Role chip */}
            <span style={{ fontSize:10, fontWeight:700, padding:'2px 8px', borderRadius:20,
              background: isDev ? 'rgba(31,163,154,0.2)' : isUser ? 'rgba(168,201,184,0.2)' : 'rgba(255,255,255,0.08)',
              color: isDev ? '#5ecec8' : isUser ? '#A8C9B8' : 'rgba(255,255,255,0.35)',
              border: `1px solid ${isDev?'rgba(31,163,154,0.3)':isUser?'rgba(168,201,184,0.25)':'rgba(255,255,255,0.1)'}` }}>
              {isDev ? '🛠 developer' : isUser ? `👤 ${user?.name?.split(' ')[0]}` : '🔓 guest'}
            </span>

            {isGuest
              ? <button onClick={()=>setShowLogin(true)} style={{fontSize:12,fontWeight:700,padding:'5px 12px',borderRadius:8,background:'#E76F51',color:'#fff',border:'none',cursor:'pointer'}}>Sign in</button>
              : <button onClick={logout} style={{fontSize:12,fontWeight:600,padding:'5px 10px',borderRadius:8,background:'rgba(255,255,255,0.08)',color:'rgba(255,255,255,0.6)',border:'1px solid rgba(255,255,255,0.12)',cursor:'pointer'}}>Sign out</button>
            }

            {isDev && (
              <button onClick={()=>setShowSettings(true)} title="API Settings"
                className="w-8 h-8 flex items-center justify-center rounded-lg transition-all"
                style={{color:'rgba(255,255,255,0.4)',background:'rgba(255,255,255,0.06)'}}>
                ⚙️
              </button>
            )}
          </div>
        </div>
      </header>

      {/* PAGES */}
      <main>
        {p === 'home'            && <HomePage {...pageProps} />}
        {p === 'organizations'   && <OrganizationsPage {...pageProps} />}
        {p === 'org-detail'      && <OrgDetailPage id={route.id} navigate={navigate} />}
        {p === 'org-new'         && <RequireAuth minRole="user" onLogin={()=>setShowLogin(true)}><OrgNewPage navigate={navigate} onSubmit={handleSubmit} /></RequireAuth>}
        {p === 'projects'        && <ProjectsPage {...pageProps} />}
        {p === 'project-detail'  && <ProjectDetailPage id={route.id} navigate={navigate} />}
        {p === 'project-new'     && <RequireAuth minRole="user" onLogin={()=>setShowLogin(true)}><ProjectNewPage navigate={navigate} onSubmit={handleSubmit} /></RequireAuth>}
        {p === 'problems'        && <RequireAuth minRole="developer" onLogin={()=>setShowLogin(true)}><ProblemsPage navigate={navigate} /></RequireAuth>}
        {p === 'problem-detail'  && <RequireAuth minRole="developer" onLogin={()=>setShowLogin(true)}><ProblemDetailPage id={route.id} navigate={navigate} /></RequireAuth>}
        {p === 'solutions'       && <RequireAuth minRole="developer" onLogin={()=>setShowLogin(true)}><SolutionsPage navigate={navigate} /></RequireAuth>}
        {p === 'solution-detail' && <RequireAuth minRole="developer" onLogin={()=>setShowLogin(true)}><SolutionDetailPage id={route.id} navigate={navigate} /></RequireAuth>}
        {p === 'process-message' && <ProcessMessagePage navigate={navigate} />}
        {p === 'messages'        && <RequireAuth minRole="developer" onLogin={()=>setShowLogin(true)}><MessagesPage navigate={navigate} /></RequireAuth>}
        {p === 'message-detail'  && <RequireAuth minRole="developer" onLogin={()=>setShowLogin(true)}><MessageDetailPage id={route.id} navigate={navigate} /></RequireAuth>}
        {p === 'my-submissions'  && <RequireAuth minRole="user" onLogin={()=>setShowLogin(true)}><MySubmissionsPage navigate={navigate} submissions={submissions} user={user} /></RequireAuth>}
        {p === 'review-queue'    && <RequireAuth minRole="developer" onLogin={()=>setShowLogin(true)}><ReviewQueuePage submissions={submissions} onReview={handleReview} /></RequireAuth>}
        {p === 'bot-test-lab'    && <RequireAuth minRole="developer" onLogin={()=>setShowLogin(true)}><BotTestLabPage /></RequireAuth>}
      </main>

      {showLogin    && <LoginModal onClose={()=>setShowLogin(false)} onSuccess={()=>setShowLogin(false)} />}
      {showSettings && <SettingsModal onClose={()=>setShowSettings(false)} />}
      <ToastProvider />
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
