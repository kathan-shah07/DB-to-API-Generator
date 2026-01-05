import { useState, useEffect } from 'react';
import { fetchJson } from '../api';
import { Play, Save, Code, Trash2 } from 'lucide-react';

export function Queries() {
    const [queries, setQueries] = useState([]);
    const [connectors, setConnectors] = useState([]);
    const [result, setResult] = useState(null);
    const [loading, setLoading] = useState(false);

    const [form, setForm] = useState({
        connector_id: '',
        name: '',
        sql_text: '',
        is_proc: false
    });

    const [previewParams, setPreviewParams] = useState({});

    const load = () => {
        fetchJson('/queries').then(setQueries).catch(console.error);
        fetchJson('/connectors').then(setConnectors).catch(console.error);
    };

    useEffect(() => { load(); }, []);

    // Extract parameters like :name from SQL
    const detectedParams = [...new Set((form.sql_text.match(/:\w+/g) || []).map(p => p.slice(1)))];

    const handleParamChange = (p, val) => {
        setPreviewParams({ ...previewParams, [p]: val });
    };

    const handleChange = (e) => {
        const val = e.target.type === 'checkbox' ? e.target.checked : e.target.value;
        setForm({ ...form, [e.target.name]: val });
    };

    const handleSave = async (e) => {
        e.preventDefault();
        try {
            await fetchJson('/queries', { method: 'POST', body: JSON.stringify(form) });
            load();
            alert('Saved');
        } catch (e) { alert(e.message); }
    };

    const handleDelete = async (e, id) => {
        e.stopPropagation();
        if (!confirm('Are you sure you want to delete this query? Any mapped endpoints will be invalidated.')) return;
        try {
            await fetchJson(`/queries/${id}`, { method: 'DELETE' });
            load();
            if (form.id === id) {
                setForm({ connector_id: '', name: '', sql_text: '', is_proc: false });
            }
        } catch (e) { alert(e.message); }
    };

    const handlePreview = async () => {
        if (!form.connector_id || !form.sql_text) return;
        setLoading(true);
        setResult(null);
        try {
            const res = await fetchJson('/queries/preview', {
                method: 'POST',
                body: JSON.stringify({
                    connector_id: form.connector_id,
                    sql_text: form.sql_text,
                    params: previewParams,
                    max_rows: 10
                })
            });
            setResult(res);
        } catch (e) { setResult({ error: e.message }); }
        setLoading(false);
    };

    const loadQuery = (q) => {
        setForm({
            id: q.id,
            connector_id: q.connector_id,
            name: q.name,
            sql_text: q.sql_text,
            is_proc: q.is_proc
        });
        setResult(null);
    };

    return (
        <div className="h-[calc(100vh-100px)] flex col">
            <h2 className="text-2xl font-bold mb-4">Query Editor</h2>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 flex-1 min-h-0">
                <div className="md:col-span-1 flex col gap-4 min-h-0">
                    <div className="card flex-1 flex col overflow-hidden">
                        <h3 className="text-sm font-bold mb-2 uppercase text-muted tracking-wide">Saved Queries</h3>
                        <div className="overflow-y-auto flex-1 flex col gap-1 pr-1">
                            {queries.map(q => (
                                <div key={q.id} className="p-3 hover:bg-white/5 rounded cursor-pointer border border-transparent hover:border-border transition group relative" onClick={() => loadQuery(q)}>
                                    <div className="font-bold text-sm mb-1">{q.name}</div>
                                    <div className="text-xs text-muted truncate font-mono opacity-60">{q.sql_text}</div>
                                    <button
                                        className="absolute right-2 top-2 opacity-0 group-hover:opacity-100 text-rose-500 hover:text-rose-400 p-1"
                                        onClick={(e) => handleDelete(e, q.id)}
                                    >
                                        <Trash2 size={14} />
                                    </button>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>

                <div className="md:col-span-2 flex col gap-4 min-h-0">
                    <div className="card flex-none">
                        <form onSubmit={handleSave} className="flex col gap-3">
                            <div className="grid grid-cols-2 gap-3">
                                <div>
                                    <label className="text-xs text-muted mb-1 block">Connector</label>
                                    <select name="connector_id" value={form.connector_id} onChange={handleChange} required className="mb-0">
                                        <option value="">-- Select --</option>
                                        {connectors.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                                    </select>
                                </div>
                                <div>
                                    <label className="text-xs text-muted mb-1 block">Query Name</label>
                                    <input name="name" value={form.name} onChange={handleChange} placeholder="Get Users" required className="mb-0" />
                                </div>
                            </div>

                            <div>
                                <label className="text-xs text-muted mb-1 block">SQL Query</label>
                                <textarea
                                    name="sql_text"
                                    value={form.sql_text}
                                    onChange={handleChange}
                                    className="h-32 font-mono text-sm leading-relaxed mb-0 bg-black/20"
                                    placeholder="SELECT * FROM users WHERE id = :id"
                                    required
                                />
                            </div>

                            {detectedParams.length > 0 && (
                                <div className="p-3 bg-white/5 border border-dashed border-border rounded">
                                    <label className="text-xs text-accent font-bold mb-2 block uppercase">Preview Parameters</label>
                                    <div className="grid grid-cols-2 gap-3">
                                        {detectedParams.map(p => (
                                            <div key={p}>
                                                <label className="text-[10px] text-muted block mb-1">{p}</label>
                                                <input
                                                    className="mb-0 text-sm py-1"
                                                    placeholder="value..."
                                                    value={previewParams[p] || ''}
                                                    onChange={e => handleParamChange(p, e.target.value)}
                                                />
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            <div className="flex justify-between items-center pt-2">
                                <label className="flex items-center gap-2 text-sm cursor-pointer select-none">
                                    <input type="checkbox" name="is_proc" checked={form.is_proc} onChange={handleChange} className="w-auto m-0" />
                                    Is Stored Procedure
                                </label>
                                <div className="flex gap-2">
                                    <button type="button" onClick={handlePreview} className="secondary flex items-center gap-2" disabled={loading}>
                                        <Play size={14} /> Preview
                                    </button>
                                    <button type="submit" className="flex items-center gap-2">
                                        <Save size={14} /> Save
                                    </button>
                                </div>
                            </div>
                        </form>
                    </div>

                    <div className="card flex-1 overflow-auto min-h-0 relative flex col border-t-4 border-t-accent">
                        <h3 className="text-sm font-bold mb-2 sticky top-0 bg-card z-10 py-1 border-b border-border flex justify-between">
                            <span>Result Preview</span>
                            {result && !result.error && <span className="text-[10px] text-green-400 font-mono">OK | {result.rows?.length} rows</span>}
                        </h3>
                        {loading && <div className="text-accent animate-pulse p-4 text-center">Running query...</div>}
                        {result && (
                            result.error ? (
                                <div className="text-red-400 font-mono text-xs whitespace-pre-wrap p-2 bg-red-900/10 rounded">{result.error}</div>
                            ) : (
                                <div className="text-xs flex-1 overflow-auto">
                                    <div className="overflow-x-auto">
                                        <table className="w-full text-left border-collapse">
                                            <thead>
                                                <tr className="bg-white/5 text-muted">
                                                    {Object.keys(result.rows?.[0] || {}).map(k => <th key={k} className="p-2 font-mono font-normal border-b border-border whitespace-nowrap">{k}</th>)}
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {result.rows?.map((row, i) => (
                                                    <tr key={i} className="border-b border-border hover:bg-white/5 transition">
                                                        {Object.values(row).map((val, j) => (
                                                            <td key={j} className="p-2 font-mono whitespace-nowrap text-gray-300">{String(val)}</td>
                                                        ))}
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            )
                        )}
                        {!result && !loading && <div className="text-muted text-center flex-1 flex items-center justify-center italic opacity-50">Enter SQL and click Preview.</div>}
                    </div>
                </div>
            </div>
        </div>
    );
}

