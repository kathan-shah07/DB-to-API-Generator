import { useState, useEffect } from 'react';
import { fetchJson } from '../api';
import { Search, Table } from 'lucide-react';

export function Schema() {
    const [connectors, setConnectors] = useState([]);
    const [selectedConn, setSelectedConn] = useState('');
    const [tables, setTables] = useState({});
    const [sample, setSample] = useState(null);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        fetchJson('/connectors').then(setConnectors).catch(console.error);
    }, []);

    const handleDiscover = async () => {
        if (!selectedConn) return;
        setLoading(true);
        try {
            const res = await fetchJson(`/connectors/${selectedConn}/discover`, { method: 'POST' });
            setTables(res.tables || {});
            setSample(null);
        } catch (e) { alert(e.message); }
        setLoading(false);
    };

    const handleViewTable = async (table) => {
        setLoading(true);
        try {
            const res = await fetchJson(`/connectors/${selectedConn}/schema/${encodeURIComponent(table)}?sample=10`);
            setSample({ table, ...res });
        } catch (e) { alert(e.message); }
        setLoading(false);
    };

    return (
        <div>
            <h2 className="text-2xl font-bold mb-6">Schema Explorer</h2>

            <div className="card mb-6">
                <div className="flex items-end gap-3">
                    <div className="flex-1">
                        <label className="block text-sm mb-1 text-muted">Select Connector</label>
                        <select value={selectedConn} onChange={e => setSelectedConn(e.target.value)}>
                            <option value="">-- Select --</option>
                            {connectors.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                        </select>
                    </div>
                    <button onClick={handleDiscover} disabled={!selectedConn || loading} className="mb-2">
                        {loading ? 'Working...' : <span className="flex items-center"><Search size={16} className="mr-2" /> Discover Tables</span>}
                    </button>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-[calc(100vh-250px)] min-h-[500px]">
                <div className="card lg:col-span-1 overflow-y-auto flex col">
                    <h3 className="text-lg font-semibold mb-3 sticky top-0 bg-card z-10 py-1 border-b border-border">Tables</h3>
                    {Object.keys(tables).length === 0 && <div className="text-muted text-sm px-1 mt-4">No tables discovered yet.</div>}
                    <div className="flex col gap-1">
                        {Object.keys(tables).map(t => (
                            <button
                                key={t}
                                className={`text-left text-sm px-3 py-2 rounded transition ${sample?.table === t ? 'bg-accent text-white' : 'hover:bg-white/5 text-muted'}`}
                                onClick={() => handleViewTable(t)}
                            >
                                <Table size={14} className="inline mr-2 opacity-70" /> {t}
                            </button>
                        ))}
                    </div>
                </div>

                <div className="card lg:col-span-2 overflow-y-auto">
                    {sample ? (
                        <>
                            <h3 className="text-lg font-semibold mb-1 flex items-center gap-2">
                                <Table size={18} /> {sample.table}
                            </h3>
                            <div className="text-xs text-muted mb-4 font-mono">
                                PK: {JSON.stringify(sample.pk)}
                            </div>

                            <h4 className="text-sm font-semibold mb-2">Columns</h4>
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-6">
                                {sample.columns?.map(c => (
                                    <div key={c.name} className="p-2 border border-border rounded text-xs bg-black/20">
                                        <div className="font-bold text-accent truncate" title={c.name}>{c.name}</div>
                                        <div className="text-muted truncate" title={c.type}>{c.type}</div>
                                    </div>
                                ))}
                            </div>

                            <h4 className="text-sm font-semibold mb-2">Sample Data (Top 10)</h4>
                            <div className="overflow-x-auto border border-border rounded">
                                <table className="w-full text-xs text-left">
                                    <thead className="bg-white/5 text-muted">
                                        <tr>
                                            {sample.columns?.map(c => <th key={c.name} className="p-2 font-normal whitespace-nowrap">{c.name}</th>)}
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {sample.sample_rows?.map((row, i) => (
                                            <tr key={i} className="border-t border-border hover:bg-white/5 transition">
                                                {sample.columns?.map(c => (
                                                    <td key={c.name} className="p-2 truncate max-w-[150px] font-mono text-gray-300 whitespace-nowrap">
                                                        {row[c.name] === null ? <span className="text-gray-600">null</span> : String(row[c.name])}
                                                    </td>
                                                ))}
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </>
                    ) : (
                        <div className="h-full flex items-center justify-center text-muted col">
                            <Table size={48} className="mb-4 opacity-20" />
                            <div>Select a table to view schema and sample data.</div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
