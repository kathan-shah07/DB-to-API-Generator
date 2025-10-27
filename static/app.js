// small helpers
function toast(msg, t = 4000) {
  const c = document.getElementById('toasts');
  const el = document.createElement('div');
  el.className = 'toast';
  el.innerText = msg;
  c.appendChild(el);
  setTimeout(() => { el.remove(); }, t);
}

function apiHeaders() {
  const key = localStorage.getItem('admin_key') || document.getElementById('admin-key').value || '';
  const headers = { 'Content-Type': 'application/json' };
  if (key && key.trim()) headers['X-API-Key'] = key.trim();
  return headers;
}

async function fetchJson(path, opts = {}) {
  const headers = Object.assign({}, opts.headers || {}, apiHeaders());
  const resp = await fetch(path, Object.assign({}, opts, { headers }));
  if (!resp.ok) {
    let txt = await resp.text().catch(() => '');
    // if auth error, update admin status badge for clarity
    try {
      const statusEl = document.getElementById('admin-status');
      if (resp.status === 401 || resp.status === 403) {
        if (statusEl) statusEl.innerText = `(auth: server ${resp.status})`;
      }
    } catch (e) { /* ignore */ }
    throw new Error('fetch failed ' + resp.status + ' ' + txt);
  }
  return resp.json();
}

async function initConnectors() {
  try {
    const list = await fetchJson('/admin/connectors');
    const sel = document.getElementById('schema-connector');
    const sel2 = document.getElementById('query-connector');
    const sel3 = document.getElementById('mapping-connector');
    [sel, sel2, sel3].forEach(s => s.innerHTML = '');
    const cl = document.getElementById('connectors-list');
    cl.innerHTML = '';
    if (!list || list.length === 0) {
      cl.innerText = 'No connectors';
      [sel, sel2, sel3].forEach(s => s.appendChild(new Option('-- none --','')));
      return;
    }
    list.forEach(c => {
      const row = document.createElement('div');
      row.className = 'connector-row';
      row.innerHTML = `<b>${c.name}</b> <small>${c.sqlalchemy_url}</small>`;
      const testBtn = document.createElement('button'); testBtn.innerText = 'Test';
      testBtn.onclick = async () => {
        try {
          const res = await fetchJson(`/admin/connectors/${c.id}/test`, { method: 'POST' });
          toast(res.ok ? `ok ${res.latency_ms}ms` : `fail ${res.error}`);
        } catch (e) { toast('test failed'); }
      };
      const delBtn = document.createElement('button'); delBtn.innerText = 'Delete';
      delBtn.onclick = async () => {
        if (!confirm('Delete connector?')) return;
        try { await fetchJson(`/admin/connectors/${c.id}`, { method: 'DELETE' }); toast('deleted'); initConnectors(); } catch (e) { toast('delete failed'); }
      };
      row.appendChild(testBtn); row.appendChild(delBtn);
      cl.appendChild(row);
      [sel, sel2, sel3].forEach(s => s.appendChild(new Option(c.name + ' (' + c.id.slice(0,6) + ')', c.id)));
    });
  } catch (e) {
    document.getElementById('connectors-list').innerText = 'Error loading connectors';
  }
}

async function initQueries() {
  try {
    const qs = await fetchJson('/admin/queries');
    const container = document.getElementById('queries-list');
    container.innerHTML = '';
    if (!qs || qs.length === 0) {
      container.innerText = 'No saved queries';
      return;
    }
    qs.forEach(q => {
      const row = document.createElement('div');
      row.className = 'query-row';
      const summary = document.createElement('div');
      summary.innerHTML = `<b>${q.name || '(no name)'}</b> <small>${q.id.slice(0,8)}</small> <div style="font-family:monospace; font-size:0.9em">${(q.sql_text || '').slice(0,200)}</div>`;
      const useBtn = document.createElement('button'); useBtn.innerText = 'Use';
      useBtn.onclick = () => {
        document.getElementById('mapping-query_id').value = q.id;
        toast('query id copied into mapping form');
        // switch to mappings tab
        switchTab('mappings');
      };
      row.appendChild(summary); row.appendChild(useBtn);
      container.appendChild(row);
    });
  } catch (e) {
    try { document.getElementById('queries-list').innerText = 'Error loading queries'; } catch (er) {}
  }
}

async function initMappings() {
  try {
    const mappings = await fetchJson('/admin/mappings');
    const ml = document.getElementById('mappings-list');
    ml.innerHTML = '';
    if (!mappings || mappings.length === 0) ml.innerText = 'No mappings';
    else {
      mappings.forEach(m => {
        const div = document.createElement('div');
        div.className = 'mapping-row';
        div.innerHTML = `<b>${m.path}</b> <span class="method">${m.method}</span> <span>${m.deployed ? 'deployed' : 'undeployed'}</span>`;
        const btn = document.createElement('button'); btn.innerText = 'Test'; btn.onclick = () => openTestModal(m);
        const deploy = document.createElement('button'); deploy.innerText = m.deployed ? 'Undeploy' : 'Deploy';
        deploy.onclick = async () => {
          try {
            if (m.deployed) {
              await fetchJson(`/admin/mappings/${m.id}/undeploy`, { method: 'POST' });
              toast('undeployed');
            } else {
              await fetchJson(`/admin/mappings/${m.id}/deploy`, { method: 'POST' });
              toast('deployed');
            }
            initMappings();
          } catch (e) { toast('deploy action failed'); }
        };
        div.appendChild(btn); div.appendChild(deploy);
        ml.appendChild(div);
      });
    }
  } catch (e) {
    document.getElementById('mappings-list').innerText = 'Error loading mappings';
  }
}

function switchTab(name) {
  document.querySelectorAll('#tabs button').forEach(b => b.classList.toggle('active', b.dataset.tab === name));
  document.querySelectorAll('.tabpanel').forEach(s => s.classList.toggle('hidden', s.id !== name));
}

function buildParamForm(params_json, container) {
  container.innerHTML = '';
  if (!params_json || params_json.length === 0) {
    container.innerHTML = '<div>No params</div>';
    return;
  }

  // group params by 'in' location
  const groups = { path: [], query: [], header: [], body: [] };
  params_json.forEach(p => {
    const loc = (p.in || 'query').toLowerCase();
    if (!groups[loc]) groups[loc] = [];
    groups[loc].push(p);
  });

  Object.keys(groups).forEach(loc => {
    const arr = groups[loc];
    if (!arr || arr.length === 0) return;
    const title = document.createElement('div'); title.className = 'param-group-title'; title.innerText = loc.toUpperCase(); container.appendChild(title);
    arr.forEach(p => {
      const row = document.createElement('div'); row.className = 'param-row';
      const label = document.createElement('label'); label.innerText = p.name + (p.required ? ' *' : '') + ' (' + (p.type || 'string') + ')';

      let input;
      if ((p.type || 'string') === 'boolean') {
        input = document.createElement('input'); input.type = 'checkbox'; input.checked = !!p.default; input.value = 'on';
      } else {
        input = document.createElement('input');
        input.type = (p.type === 'integer' || p.type === 'number') ? 'number' : 'text';
        if (p.default !== undefined) input.value = String(p.default);
        input.placeholder = p.default !== undefined ? String(p.default) : '';
      }

      input.name = p.name;
      input.dataset.paramIn = loc;
      if (p.required) input.dataset.required = '1';

      row.appendChild(label); row.appendChild(input); container.appendChild(row);
    });
  });
}

function gatherFormParams(container) {
  // returns params grouped by location: { path: {}, query: {}, header: {}, body: {} }
  const inputs = container.querySelectorAll('input');
  const out = { path: {}, query: {}, header: {}, body: {} };
  inputs.forEach(i => {
    const name = i.name;
    const loc = i.dataset.paramIn || 'query';
    if (i.type === 'checkbox') {
      // boolean
      out[loc][name] = i.checked;
    } else if (i.type === 'number') {
      if (i.value === '') return;
      out[loc][name] = Number(i.value);
    } else {
      if (i.value === '') return;
      out[loc][name] = i.value;
    }
  });
  return out;
}

function openTestModal(m) {
  const modal = document.getElementById('modal');
  const body = document.getElementById('modal-body');
  document.getElementById('modal-title').innerText = `Test ${m.method} ${m.path}`;
  body.innerHTML = '';
  const info = document.createElement('div'); info.innerHTML = `<div>Auth required: ${m.auth_required}</div>`; body.appendChild(info);
  // params_json may be string or object
  let params = m.params_json;
  if (typeof params === 'string' && params.trim()) {
    try { params = JSON.parse(params); } catch (e) { params = []; }
  }
  const paramsContainer = document.createElement('div'); paramsContainer.id = 'modal-params'; body.appendChild(paramsContainer);
  // resolved request preview (shows final URL and headers before running)
  const resolvedDiv = document.createElement('pre');
  resolvedDiv.id = 'modal-resolved';
  resolvedDiv.style.whiteSpace = 'pre-wrap';
  resolvedDiv.style.maxHeight = '80px';
  resolvedDiv.style.overflow = 'auto';
  resolvedDiv.innerText = `URL: ${m.path}\nMethod: ${m.method || 'GET'}\nHeaders: ${JSON.stringify(apiHeaders(), null, 2)}`;
  body.appendChild(resolvedDiv);
  buildParamForm(params, paramsContainer);
  const responseBox = document.createElement('pre'); responseBox.id = 'modal-response'; responseBox.style.maxHeight = '200px'; responseBox.style.overflow = 'auto'; body.appendChild(responseBox);
  // attach run handler
  document.getElementById('modal-run').onclick = async () => {
    const grouped = gatherFormParams(paramsContainer);
    try {
      let url = m.path;
      // substitute path params in {name} or :name
      Object.entries(grouped.path || {}).forEach(([k, v]) => {
        url = url.replace(new RegExp('\\{' + k + '\\}', 'g'), encodeURIComponent(String(v)));
        url = url.replace(new RegExp(':' + k + '\\b', 'g'), encodeURIComponent(String(v)));
      });

      // build query string
      const qs = new URLSearchParams();
      Object.entries(grouped.query || {}).forEach(([k, v]) => qs.append(k, String(v)));
      const fullUrl = qs.toString() ? `${url}?${qs.toString()}` : url;

      // build headers (merge with apiHeaders)
      const headers = Object.assign({}, apiHeaders());
      Object.entries(grouped.header || {}).forEach(([k, v]) => { headers[k] = String(v); });

      const method = (m.method || 'GET').toUpperCase();
      // update resolved preview before making request
      try {
        const rd = document.getElementById('modal-resolved');
        if (rd) rd.innerText = `URL: ${fullUrl}\nMethod: ${method}\nHeaders: ${JSON.stringify(headers, null, 2)}`;
      } catch (e) { /* ignore */ }
      let resp;
      if (method === 'GET' || method === 'DELETE') {
        resp = await fetch(fullUrl, { method, headers });
      } else {
        // body params -> JSON
        const body = Object.keys(grouped.body || {}).length ? grouped.body : grouped.query || {};
        resp = await fetch(fullUrl, { method, headers: headers, body: JSON.stringify(body) });
      }

      const statusLine = `HTTP ${resp.status} ${resp.statusText}`;
      let text = await resp.text();
      let parsed;
      try { parsed = JSON.parse(text); } catch (e) { parsed = null; }
      const headersObj = {};
      resp.headers.forEach((v, k) => { headersObj[k] = v; });

      responseBox.innerText = JSON.stringify({ status: statusLine, headers: headersObj, body: parsed !== null ? parsed : text }, null, 2);
    } catch (e) { responseBox.innerText = String(e); }
  };
  modal.classList.remove('hidden');
}

document.addEventListener('DOMContentLoaded', () => {
  // ensure modal is hidden (defensive) and admin key input is enabled & focused
  try {
    const modalEl = document.getElementById('modal');
    if (modalEl) modalEl.classList.add('hidden');
    const adminInput = document.getElementById('admin-key');
    if (adminInput) { adminInput.removeAttribute('disabled'); adminInput.autocomplete = 'off'; adminInput.focus(); }
  } catch (e) { /* ignore */ }
  // tab handling
  document.querySelectorAll('#tabs button').forEach(b => b.addEventListener('click', () => switchTab(b.dataset.tab)));

  // admin key
  document.getElementById('save-key').addEventListener('click', async () => {
    try {
      const val = document.getElementById('admin-key').value || '';
      localStorage.setItem('admin_key', val);
      toast('key saved');
      // refresh lists (best-effort)
      try { await initConnectors(); } catch (e) { /* ignore */ }
      try { await initMappings(); } catch (e) { /* ignore */ }
      try { await checkAdminAuth(); } catch (e) { /* ignore */ }
    } catch (e) { toast('save key failed'); }
  });
  const saved = localStorage.getItem('admin_key'); if (saved) document.getElementById('admin-key').value = saved;
  // save on Enter in admin key input
  document.getElementById('admin-key').addEventListener('keydown', async (ev) => {
    if (ev.key === 'Enter') {
      ev.preventDefault();
      document.getElementById('save-key').click();
    }
  });

  // connector form
  document.getElementById('connector-form').addEventListener('submit', async (ev) => {
    ev.preventDefault(); const fd = new FormData(ev.target); const payload = { name: fd.get('name'), sqlalchemy_url: fd.get('sqlalchemy_url') };
    try { await fetchJson('/admin/connectors', { method: 'POST', body: JSON.stringify(payload) }); toast('connector added'); ev.target.reset(); initConnectors(); } catch (e) { toast('add connector failed'); }
  });

  // discover
  document.getElementById('discover-btn').addEventListener('click', async () => {
    const cid = document.getElementById('schema-connector').value; if (!cid) { toast('select connector'); return; }
    try {
      const res = await fetchJson(`/admin/connectors/${cid}/discover`, { method: 'POST' });
      const tables = res.tables || {};
      const tdiv = document.getElementById('schema-tables'); tdiv.innerHTML = '';
      Object.keys(tables).forEach(tbl => {
        const btn = document.createElement('button'); btn.innerText = tbl; btn.onclick = async () => {
          try {
            const info = await fetchJson(`/admin/connectors/${cid}/schema/${encodeURIComponent(tbl)}?sample=10`);
            document.getElementById('schema-sample').innerText = JSON.stringify(info, null, 2);
          } catch (e) { toast('table fetch failed'); }
        };
        tdiv.appendChild(btn);
      });
    } catch (e) { toast('discover failed'); }
  });

  // query form
  document.getElementById('query-form').addEventListener('submit', async (ev) => {
    ev.preventDefault(); const fd = new FormData(ev.target);
    const payload = { connector_id: document.getElementById('query-connector').value, name: fd.get('name'), sql_text: fd.get('sql_text'), is_proc: !!fd.get('is_proc') };
    try { const res = await fetchJson('/admin/queries', { method: 'POST', body: JSON.stringify(payload) }); toast('query saved ' + res.id); ev.target.reset(); } catch (e) { toast('save query failed'); }
    try { await initQueries(); } catch (e) { /* ignore */ }
  });
  document.getElementById('preview-query').addEventListener('click', async () => {
    const conn = document.getElementById('query-connector').value; const sql = document.querySelector('#query-form textarea[name="sql_text"]').value;
    try { const res = await fetchJson('/admin/queries/preview', { method: 'POST', body: JSON.stringify({ connector_id: conn, sql_text: sql, params: {}, max_rows: 10 }) }); document.getElementById('query-result').innerText = JSON.stringify(res, null, 2); } catch (e) { toast('preview failed'); }
  });

  // mapping create
  document.getElementById('mapping-form').addEventListener('submit', async (ev) => {
    ev.preventDefault(); const payload = { query_id: document.getElementById('mapping-query_id').value, connector_id: document.getElementById('mapping-connector').value, path: document.getElementById('mapping-path').value, method: document.getElementById('mapping-method').value, params_json: JSON.parse(document.getElementById('mapping-params_json').value || '[]'), auth_required: document.getElementById('mapping-auth').checked };
    try { const res = await fetchJson('/admin/mappings', { method: 'POST', body: JSON.stringify(payload) }); toast('mapping created ' + res.id); ev.target.reset(); initMappings(); } catch (e) { toast('create mapping failed'); }
  });

  // apikey create
  document.getElementById('apikey-form').addEventListener('submit', async (ev) => {
    ev.preventDefault(); const role = document.getElementById('apikey-role').value;
    try { const res = await fetchJson('/admin/api-keys', { method: 'POST', body: JSON.stringify({ role }) }); document.getElementById('apikey-result').innerText = 'Token: ' + res.token + ' (copy this now)'; } catch (e) { toast('create key failed'); }
  });

  // logs
  document.getElementById('logs-form').addEventListener('submit', async (ev) => {
    ev.preventDefault(); const id = document.getElementById('logs-request-id').value; if (!id) return; try { const res = await fetchJson('/admin/logs/' + id); document.getElementById('log-result').innerText = JSON.stringify(res, null, 2); } catch (e) { toast('log fetch failed'); }
  });

  // modal close
  document.getElementById('modal-close').addEventListener('click', () => document.getElementById('modal').classList.add('hidden'));

  // admin test button
  document.getElementById('admin-test').addEventListener('click', async () => {
    try {
      await checkAdminAuth();
    } catch (e) { toast('auth test failed'); }
  });

  // initial load
  initConnectors(); initMappings(); initQueries();
  // check admin auth on load
  try { checkAdminAuth(); } catch (e) { /* ignore */ }
});

async function checkAdminAuth() {
  const statusEl = document.getElementById('admin-status');
  statusEl.innerText = '(auth: checking)';
  try {
    // call a cheap admin endpoint to verify key
    const res = await fetch('/admin/connectors', { headers: apiHeaders() });
    if (!res.ok) {
      statusEl.innerText = `(auth: server ${res.status})`;
      return false;
    }
    statusEl.innerText = '(auth: ok)';
    return true;
  } catch (e) {
    statusEl.innerText = '(auth: error)';
    return false;
  }
}
