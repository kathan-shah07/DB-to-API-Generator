import { useState, useEffect } from 'react';
import { fetchJson } from '../api';
import { ArrowRight, Globe, Lock, Unlock, Play, Code, Trash2 } from 'lucide-react';

export function Mappings() {
    const [mappings, setMappings] = useState([]);
    const [queries, setQueries] = useState([]);
    const [connectors, setConnectors] = useState([]);
    const [loading, setLoading] = useState(false);

    // Form
    const [form, setForm] = useState({
        query_id: '',
        connector_id: '',
        path: '',
        method: 'GET',
        params_json: '[]',
        auth_required: true
    });

    const [params, setParams] = useState([]);

    const load = () => {
        setLoading(true);
        Promise.all([
            fetchJson('/mappings').then(setMappings),
            fetchJson('/queries').then(setQueries),
            fetchJson('/connectors').then(setConnectors)
        ]).finally(() => setLoading(false));
    };

    useEffect(() => { load(); }, []);

    // Effect to suggest parameters based on SQL and Path
    useEffect(() => {
        const selectedQuery = queries.find(q => q.id === form.query_id);
        const sqlText = selectedQuery?.sql_text || '';
        const path = form.path || '';

        const sqlParams = (sqlText.match(/:\w+/g) || []).map(p => p.slice(1));
        const pathParams = (path.match(/:(\w+)/g) || []).map(p => p.slice(1));
        const braceParams = (path.match(/{(\w+)}/g) || []).map(p => p.slice(1, -1));

        const allKeys = [...new Set([...sqlParams, ...pathParams, ...braceParams])];

        // Merge with existing params state to keep customizations
        setParams(prev => {
            const next = allKeys.map(k => {
                const existing = prev.find(p => p.name === k);
                if (existing) return existing;
                // Auto-detect 'in' based on presence in path
                const isInPath = path.includes(`:${k}`) || path.includes(`{${k}}`);
                return { name: k, in: isInPath ? 'path' : 'query', type: 'string', required: true };
            });
            return next;
        });
    }, [form.query_id, form.path, queries]);

    const handleChange = (e) => {
        const val = e.target.type === 'checkbox' ? e.target.checked : e.target.value;
        setForm({ ...form, [e.target.name]: val });
    };

    const updateParam = (index, field, val) => {
        const next = [...params];
        next[index] = { ...next[index], [field]: val };
        setParams(next);
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        try {
            // Normalize path for FastAPI (ensure :name becomes {name})
            let normalizedPath = form.path;
            params.forEach(p => {
                if (p.in === 'path') {
                    // Replace :id with {id} for FastAPI compatibility
                    normalizedPath = normalizedPath.replace(new RegExp(':' + p.name + '\\b', 'g'), '{' + p.name + '}');
                }
            });

            await fetchJson('/mappings', {
                method: 'POST',
                body: JSON.stringify({ ...form, path: normalizedPath, params_json: params })
            });
            alert('Mapping created');
            setForm({ ...form, path: '', query_id: '' });
            setParams([]);
            load();
        } catch (e) { alert(e.message); }
    };

    const toggleDeploy = async (m) => {
        try {
            if (m.deployed) {
                await fetchJson(`/mappings/${m.id}/undeploy`, { method: 'POST' });
            } else {
                await fetchJson(`/mappings/${m.id}/deploy`, { method: 'POST' });
            }
            load();
        } catch (e) { alert(e.message); }
    };

    const handleDelete = async (id) => {
        if (!confirm('Are you sure you want to delete this mapping?')) return;
        try {
            await fetchJson(`/mappings/${id}`, { method: 'DELETE' });
            load();
        } catch (e) { alert(e.message); }
    };

    const onQuerySelect = (e) => {
        const qId = e.target.value;
        const q = queries.find(x => x.id === qId);
        if (q) {
            setForm(f => ({ ...f, query_id: qId, connector_id: q.connector_id }));
        } else {
            setForm(f => ({ ...f, query_id: qId }));
        }
    };

    return (
        <div>
            <h2 className="text-2xl font-bold mb-6">API Mappings</h2>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="card lg:col-span-1 border-t-4 border-t-accent flex col">
                    <h3 className="text-lg font-semibold mb-4">Create Endpoint</h3>
                    <form onSubmit={handleSubmit} className="flex col gap-3">
                        <div>
                            <label className="text-xs text-muted block mb-1">Source Query</label>
                            <select name="query_id" value={form.query_id} onChange={onQuerySelect} required className="mb-0">
                                <option value="">-- Select --</option>
                                {queries.map(q => <option key={q.id} value={q.id}>{q.name}</option>)}
                            </select>
                        </div>

                        <div className="flex gap-2">
                            <div className="w-1/3">
                                <label className="text-xs text-muted block mb-1">Method</label>
                                <select name="method" value={form.method} onChange={handleChange} className="mb-0">
                                    {['GET', 'POST', 'PUT', 'DELETE'].map(m => <option key={m}>{m}</option>)}
                                </select>
                            </div>
                            <div className="flex-1">
                                <label className="text-xs text-muted block mb-1">Path (e.g. /api/user/:id)</label>
                                <input name="path" value={form.path} onChange={handleChange} placeholder="/api/users" required className="mb-0" />
                            </div>
                        </div>

                        {params.length > 0 && (
                            <div className="mt-2">
                                <label className="text-xs text-accent font-bold mb-2 block uppercase">Parameter Builder</label>
                                <div className="flex col gap-2 bg-black/20 p-2 rounded max-h-60 overflow-y-auto border border-border">
                                    {params.map((p, i) => (
                                        <div key={p.name} className="flex col gap-1 p-2 bg-card border border-border rounded text-[10px]">
                                            <div className="font-bold flex justify-between items-center text-accent">
                                                <span>{p.name}</span>
                                                <span className="opacity-50 uppercase text-[8px]">{p.in}</span>
                                            </div>
                                            <div className="flex gap-1">
                                                <select className="p-1 m-0 text-[10px]" value={p.in} onChange={e => updateParam(i, 'in', e.target.value)}>
                                                    <option value="path">Path</option>
                                                    <option value="query">Query</option>
                                                    <option value="body">Body (JSON)</option>
                                                    <option value="header">Header</option>
                                                </select>
                                                <select className="p-1 m-0 text-[10px]" value={p.type} onChange={e => updateParam(i, 'type', e.target.value)}>
                                                    <option value="string">String</option>
                                                    <option value="integer">Integer</option>
                                                    <option value="number">Float</option>
                                                    <option value="boolean">Boolean</option>
                                                </select>
                                                <label className="flex items-center gap-1 select-none">
                                                    <input type="checkbox" checked={p.required} onChange={e => updateParam(i, 'required', e.target.checked)} className="w-auto m-0 h-3 w-3" />
                                                    Required
                                                </label>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        <div className="py-2 border-t border-border mt-2">
                            <label className="flex items-center gap-2 text-sm select-none cursor-pointer">
                                <input type="checkbox" name="auth_required" checked={form.auth_required} onChange={handleChange} className="w-auto m-0" />
                                Require Admin API Key
                            </label>
                        </div>

                        <button type="submit" className="w-full">Save & Deployed</button>
                    </form>
                </div>

                <div className="lg:col-span-2">
                    <div className="card">
                        <div className="flex justify-between items-center mb-6">
                            <h3 className="text-lg font-semibold">Live Endpoints</h3>
                            <button className="secondary text-sm px-3 py-1" onClick={load}>Refresh</button>
                        </div>

                        <div className="flex col gap-4">
                            {mappings.length === 0 && <div className="text-muted text-center py-8">No mappings created yet.</div>}
                            {mappings.map(m => (
                                <div key={m.id} className="p-4 border border-border rounded-lg bg-white/5 group hover:bg-white/[0.07] transition-all">
                                    <div className="flex items-start justify-between">
                                        <div className="flex-1 overflow-hidden">
                                            <div className="flex items-center gap-3">
                                                <span className={`text-[10px] font-bold px-2 py-0.5 rounded shadow-sm ${getMethodColor(m.method)} text-white`}>
                                                    {m.method}
                                                </span>
                                                <span className="font-mono text-sm font-medium truncate tracking-tight">{m.path}</span>
                                            </div>
                                            <div className="flex items-center gap-4 mt-2 text-[11px] text-muted">
                                                <span className="flex items-center gap-1">
                                                    {m.auth_required ? <Lock size={12} className="text-yellow-500" /> : <Unlock size={12} className="text-green-500" />}
                                                    {m.auth_required ? 'Secure' : 'Public'}
                                                </span>
                                                <span className="flex items-center gap-1">
                                                    <Code size={12} /> {queries.find(q => q.id === m.query_id)?.name || 'Unknown Query'}
                                                </span>
                                                <span className={`flex items-center gap-1 ${m.deployed ? 'text-green-400' : 'text-gray-500'}`}>
                                                    <Globe size={12} /> {m.deployed ? 'Active' : 'Offline'}
                                                </span>
                                            </div>
                                        </div>
                                        <div className="flex gap-2">
                                            <button
                                                className={`text-[11px] px-3 py-1 font-bold uppercase transition-all ${m.deployed ? 'danger' : 'accent'}`}
                                                onClick={() => toggleDeploy(m)}
                                            >
                                                {m.deployed ? 'Undeploy' : 'Deploy'}
                                            </button>
                                            <button
                                                className="secondary text-rose-500 hover:text-rose-400 p-1"
                                                onClick={() => handleDelete(m.id)}
                                            >
                                                <Trash2 size={16} />
                                            </button>
                                        </div>
                                    </div>

                                    {m.params_json?.length > 0 && (
                                        <div className="mt-4 pt-3 border-t border-border flex flex-wrap gap-2">
                                            {m.params_json.map(arg => (
                                                <span key={arg.name} className="bg-black/30 px-2 py-0.5 rounded text-[10px] font-mono border border-border/50 text-muted">
                                                    <span className="text-accent">{arg.in}:</span>{arg.name} <span className="opacity-40 italic">({arg.type})</span>
                                                </span>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

function getMethodColor(m) {
    if (m === 'GET') return 'bg-blue-600';
    if (m === 'POST') return 'bg-emerald-600';
    if (m === 'DELETE') return 'bg-rose-600';
    if (m === 'PUT') return 'bg-amber-600';
    return 'bg-gray-600';
}
