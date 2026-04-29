/* hate2action — API client */
window.api = (() => {
  const STORAGE_KEY = 'h2a_config';

  function getConfig() {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}'); }
    catch { return {}; }
  }
  function saveConfig(cfg) { localStorage.setItem(STORAGE_KEY, JSON.stringify(cfg)); }

  async function request(path, options = {}) {
    const cfg = getConfig();
    const baseURL = cfg.baseURL || window.location.origin;
    const apiKey = cfg.apiKey || '';
    const res = await fetch(`${baseURL}${path}`, {
      ...options,
      headers: { 'Content-Type': 'application/json', 'X-API-Key': apiKey, ...(options.headers || {}) },
    });
    if (!res.ok) {
      const txt = await res.text().catch(() => '');
      throw new Error(`${res.status} ${res.statusText}${txt ? ': ' + txt.slice(0, 120) : ''}`);
    }
    if (res.status === 204) return null;
    return res.json();
  }

  const json = (data) => JSON.stringify(data);

  return {
    getConfig, saveConfig,
    // Organizations
    getOrganizations:    ()        => request('/organizations'),
    getOrganization:     (id)      => request(`/organizations/${id}`),
    createOrganization:  (data)    => request('/organizations',    { method: 'POST',   body: json(data) }),
    updateOrganization:  (id, data)=> request(`/organizations/${id}`, { method: 'PUT',body: json(data) }),
    deleteOrganization:  (id)      => request(`/organizations/${id}`, { method: 'DELETE' }),
    // Projects
    getProjects:    ()        => request('/projects'),
    getProject:     (id)      => request(`/projects/${id}`),
    createProject:  (data)    => request('/projects',       { method: 'POST',   body: json(data) }),
    updateProject:  (id, data)=> request(`/projects/${id}`, { method: 'PUT',    body: json(data) }),
    deleteProject:  (id)      => request(`/projects/${id}`, { method: 'DELETE' }),
    // Problems
    getProblems:    ()        => request('/problems'),
    getProblem:     (id)      => request(`/problems/${id}`),
    createProblem:  (data)    => request('/problems',       { method: 'POST',   body: json(data) }),
    updateProblem:  (id, data)=> request(`/problems/${id}`, { method: 'PUT',    body: json(data) }),
    deleteProblem:  (id)      => request(`/problems/${id}`, { method: 'DELETE' }),
    // Solutions
    getSolutions:    ()        => request('/solutions'),
    getSolution:     (id)      => request(`/solutions/${id}`),
    createSolution:  (data)    => request('/solutions',       { method: 'POST',   body: json(data) }),
    updateSolution:  (id, data)=> request(`/solutions/${id}`, { method: 'PUT',    body: json(data) }),
    deleteSolution:  (id)      => request(`/solutions/${id}`, { method: 'DELETE' }),
    // Messages
    getMessages: ()   => request('/messages'),
    getMessage:  (id) => request(`/messages/${id}`),
    // Process message
    processMessage: (message, response_style) =>
      request('/process-message', { method: 'POST', body: json({ message, response_style }) }),
  };
})();
