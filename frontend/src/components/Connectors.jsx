import { useState, useEffect } from 'react';
import { fetchJson } from '../api';
import { Trash2, Plus, Zap, Database, Server, User, Lock, Settings } from 'lucide-react';

export function Connectors() {
    const [list, setList] = useState([]);
    const [drivers, setDrivers] = useState([]);
    const [loading, setLoading] = useState(false);
    const [dbType, setDbType] = useState('sqlite');
    const [form, setForm] = useState({
        name: '',
        sqlite_path: 'sample.db',
        host: '',
        port: '',
        database: '',
        username: '',
        password: '',
        driver: '',
        custom_url: ''
    });

    const load = async () => {
        setLoading(true);
        try {
            const data = await fetchJson('/connectors');
            setList(data);
        } catch (e) {
            console.error(e);
        }
        setLoading(false);
    };

    const loadDrivers = async () => {
        try {
            const data = await fetchJson('/drivers/odbc');
            setDrivers(data || []);
            if (data && data.length > 0) {
                // Set default driver if not set
                setForm(prev => ({ ...prev, driver: data.find(d => d.includes('SQL Server')) || data[0] }));
            }
        } catch (e) { console.error(e); }
    };

    useEffect(() => {
        load();
        loadDrivers();
    }, []);

    const handleChange = (e) => {
        setForm({ ...form, [e.target.name]: e.target.value });
    };

    const handleDelete = async (id) => {
        if (!confirm('Delete this connector? All associated schemas and queries will remain but the connection will be lost.')) return;
        try {
            await fetchJson(`/connectors/${id}`, { method: 'DELETE' });
            load();
        } catch (e) { alert(e.message); }
    };

    const handleTest = async (id) => {
        try {
            const res = await fetchJson(`/connectors/${id}/test`, { method: 'POST' });
            alert(res.ok ? `Connection Success! Latency: ${res.latency_ms}ms` : `Connection Failed: ${res.error}`);
        } catch (e) { alert(e.message); }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        let sqlalchemy_url = '';

        if (dbType === 'sqlite') {
            sqlalchemy_url = `sqlite:///${form.sqlite_path}`;
        } else if (dbType === 'mssql') {
            const encodedPass = encodeURIComponent(form.password);
            const portStr = form.port ? `:${form.port}` : '';
            sqlalchemy_url = `mssql+pyodbc://${form.username}:${encodedPass}@${form.host}${portStr}/${form.database}?driver=${encodeURIComponent(form.driver)}`;
        } else if (dbType === 'postgres') {
            const encodedPass = encodeURIComponent(form.password);
            const portStr = form.port ? `:${form.port}` : ':5432';
            sqlalchemy_url = `postgresql://${form.username}:${encodedPass}@${form.host}${portStr}/${form.database}`;
        } else if (dbType === 'mysql') {
            const encodedPass = encodeURIComponent(form.password);
            const portStr = form.port ? `:${form.port}` : ':3306';
            sqlalchemy_url = `mysql+pymysql://${form.username}:${encodedPass}@${form.host}${portStr}/${form.database}`;
        } else {
            sqlalchemy_url = form.custom_url;
        }

        try {
            await fetchJson('/connectors', {
                method: 'POST',
                body: JSON.stringify({
                    name: form.name,
                    sqlalchemy_url
                })
            });
            setForm({ ...form, name: '', custom_url: '', host: '', database: '', username: '', password: '' });
            load();
        } catch (e) { alert(e.message); }
    };

    return (
        <div className="flex col gap-6">
            <h2 className="text-2xl font-bold">Database Connectors</h2>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                <div className="lg:col-span-5 flex col gap-4">
                    <div className="card border-t-4 border-t-accent shadow-xl">
                        <h3 className="text-lg font-semibold flex items-center gap-2 mb-4 text-accent">
                            <Plus size={20} /> Add New Connection
                        </h3>

                        <div className="flex gap-2 mb-6 bg-black/20 p-1 rounded-lg">
                            {['sqlite', 'mssql', 'postgres', 'mysql', 'custom'].map(t => (
                                <button
                                    key={t}
                                    onClick={() => setDbType(t)}
                                    className={`flex-1 py-1 px-2 text-[10px] font-bold uppercase rounded transition-all ${dbType === t ? 'bg-accent text-white shadow-lg' : 'text-muted hover:text-white'}`}
                                >
                                    {t}
                                </button>
                            ))}
                        </div>

                        <form onSubmit={handleSubmit} className="flex col gap-4">
                            <div>
                                <label className="text-xs text-muted mb-1 block uppercase font-bold tracking-wider">Internal Name</label>
                                <input name="name" value={form.name} onChange={handleChange} placeholder="e.g. My-Production-DB" required className="bg-black/20 border-border" />
                            </div>

                            {dbType === 'sqlite' && (
                                <div>
                                    <label className="text-xs text-muted mb-1 block uppercase font-bold tracking-wider">SQLite File Path</label>
                                    <div className="relative">
                                        <Database className="absolute left-3 top-3 text-muted" size={16} />
                                        <input name="sqlite_path" value={form.sqlite_path} onChange={handleChange} placeholder="sample.db" required className="pl-10 bg-black/20 border-border" />
                                    </div>
                                </div>
                            )}

                            {(dbType === 'mssql' || dbType === 'postgres' || dbType === 'mysql') && (
                                <div className="flex col gap-4">
                                    <div className="grid grid-cols-3 gap-2">
                                        <div className="col-span-2">
                                            <label className="text-xs text-muted mb-1 block uppercase font-bold tracking-wider">Host / Address</label>
                                            <div className="relative">
                                                <Server className="absolute left-3 top-3 text-muted" size={16} />
                                                <input name="host" value={form.host} onChange={handleChange} placeholder="localhost or 10.0.0.5" required className="pl-10 bg-black/20 border-border" />
                                            </div>
                                        </div>
                                        <div>
                                            <label className="text-xs text-muted mb-1 block uppercase font-bold tracking-wider">Port</label>
                                            <input name="port" value={form.port} onChange={handleChange} placeholder={dbType === 'mssql' ? '1433' : (dbType === 'postgres' ? '5432' : '3306')} className="bg-black/20 border-border" />
                                        </div>
                                    </div>

                                    <div>
                                        <label className="text-xs text-muted mb-1 block uppercase font-bold tracking-wider">Database Name</label>
                                        <div className="relative">
                                            <Database className="absolute left-3 top-3 text-muted" size={16} />
                                            <input name="database" value={form.database} onChange={handleChange} placeholder="master" required className="pl-10 bg-black/20 border-border" />
                                        </div>
                                    </div>

                                    <div className="grid grid-cols-2 gap-2">
                                        <div>
                                            <label className="text-xs text-muted mb-1 block uppercase font-bold tracking-wider">Username</label>
                                            <div className="relative">
                                                <User className="absolute left-3 top-3 text-muted" size={16} />
                                                <input name="username" value={form.username} onChange={handleChange} placeholder="sa" required className="pl-10 bg-black/20 border-border" />
                                            </div>
                                        </div>
                                        <div>
                                            <label className="text-xs text-muted mb-1 block uppercase font-bold tracking-wider">Password</label>
                                            <div className="relative">
                                                <Lock className="absolute left-3 top-3 text-muted" size={16} />
                                                <input name="password" type="password" value={form.password} onChange={handleChange} placeholder="••••••••" required className="pl-10 bg-black/20 border-border" />
                                            </div>
                                        </div>
                                    </div>

                                    {dbType === 'mssql' && (
                                        <div>
                                            <label className="text-xs text-muted mb-1 block uppercase font-bold tracking-wider">ODBC Driver</label>
                                            <div className="relative text-black">
                                                <Settings className="absolute left-3 top-3 text-muted" size={16} />
                                                <select name="driver" value={form.driver} onChange={handleChange} required className="pl-10 bg-black/20 border-border appearance-none w-full">
                                                    {drivers.length === 0 && <option value="">No drivers found</option>}
                                                    {drivers.map(d => <option key={d} value={d}>{d}</option>)}
                                                </select>
                                            </div>
                                            <p className="text-[10px] text-muted mt-1 italic">We detected these drivers on your system.</p>
                                        </div>
                                    )}
                                </div>
                            )}

                            {dbType === 'custom' && (
                                <div>
                                    <label className="text-xs text-muted mb-1 block uppercase font-bold tracking-wider">Custom SQLAlchemy URL</label>
                                    <textarea
                                        name="custom_url"
                                        value={form.custom_url}
                                        onChange={handleChange}
                                        placeholder="mssql+pyodbc://user:pass@host/db?driver=..."
                                        required
                                        className="bg-black/20 border-border h-24"
                                    />
                                </div>
                            )}

                            <button type="submit" className="w-full font-bold py-3 mt-4 flex items-center justify-center gap-2 shadow-lg">
                                <Plus size={18} /> Add Database Connector
                            </button>
                        </form>
                    </div>
                </div>

                <div className="lg:col-span-7">
                    <div className="card h-full flex col border-t-4 border-t-white/20">
                        <div className="flex justify-between items-center mb-6">
                            <h3 className="text-lg font-semibold flex items-center gap-2">
                                <Server size={20} className="text-muted" /> Configured Connectors
                            </h3>
                            <button className="secondary text-xs py-1 px-3" onClick={load}>Refresh</button>
                        </div>

                        {loading ? (
                            <div className="flex-1 flex col items-center justify-center text-muted gap-3 opacity-50">
                                <div className="w-10 h-10 border-4 border-accent border-t-transparent rounded-full animate-spin"></div>
                                <span>Scanning active connections...</span>
                            </div>
                        ) : (
                            <div className="flex col gap-4 overflow-y-auto max-h-[600px] pr-2">
                                {list.length === 0 && (
                                    <div className="text-muted text-center py-12 border-2 border-dashed border-border rounded-xl">
                                        No databases connected yet. Use the form on the left to get started.
                                    </div>
                                )}
                                {list.map(c => (
                                    <div key={c.id} className="p-5 border border-border rounded-xl bg-white/5 hover:bg-white/[0.08] transition-all group shadow-sm flex items-center justify-between">
                                        <div className="flex-1 min-w-0 pr-4">
                                            <div className="font-bold text-base flex items-center gap-2 text-white">
                                                <span className={`w-2 h-2 rounded-full ${c.sqlalchemy_url.startsWith('sqlite') ? 'bg-cyan-500' : 'bg-emerald-500'} shadow-[0_0_8px_rgba(0,0,0,0.5)]`}></span>
                                                {c.name}
                                            </div>
                                            <div className="text-xs text-muted mt-2 font-mono truncate opacity-60 bg-black/30 p-2 rounded border border-white/5">
                                                {c.sqlalchemy_url.replace(/:([^@]+)@/, ':****@')}
                                            </div>
                                        </div>
                                        <div className="flex gap-2">
                                            <button
                                                className="secondary text-xs px-4 py-2 font-bold hover:bg-accent hover:text-white transition-all shadow-sm flex items-center gap-2"
                                                onClick={() => handleTest(c.id)}
                                            >
                                                <Zap size={14} /> Test
                                            </button>
                                            <button
                                                className="bg-black/40 hover:bg-rose-900/50 text-rose-500 p-2 rounded-lg border border-rose-500/20 transition-all shadow-sm"
                                                onClick={() => handleDelete(c.id)}
                                                title="Delete connection"
                                            >
                                                <Trash2 size={18} />
                                            </button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
