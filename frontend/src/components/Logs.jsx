import { useState } from 'react';
import { fetchJson } from '../api';
import { Search, Clock, FileText } from 'lucide-react';

export function Logs() {
    const [reqId, setReqId] = useState('');
    const [log, setLog] = useState(null);
    const [error, setError] = useState(null);

    const handleSearch = async (e) => {
        e.preventDefault();
        setError(null);
        setLog(null);
        try {
            const data = await fetchJson(`/logs/${reqId}`);
            setLog(data);
        } catch (e) { setError(e.message); }
    };

    return (
        <div className="max-w-4xl mx-auto">
            <h2 className="text-2xl font-bold mb-6">Request Logs</h2>

            <div className="card mb-6">
                <form onSubmit={handleSearch} className="flex gap-4">
                    <input
                        value={reqId}
                        onChange={e => setReqId(e.target.value)}
                        placeholder="Request ID (UUID)"
                        className="flex-1 mb-0"
                        required
                    />
                    <button type="submit" className="flex items-center gap-2">
                        <Search size={16} /> Search
                    </button>
                </form>
            </div>

            {error && <div className="p-4 bg-red-900/20 text-red-400 border border-red-900 rounded mb-4 flex items-center gap-2">
                <divWrapper>Error: {error}</divWrapper>
            </div>}

            {log && (
                <div className="card">
                    <div className="flex justify-between items-start mb-6 border-b border-border pb-4">
                        <h3 className="text-lg font-bold flex items-center gap-2">
                            <FileText size={20} /> Request Details
                        </h3>
                        <div className={`px-3 py-1 rounded text-sm font-bold ${log.status === 'ok' ? 'bg-green-900/50 text-green-300' : 'bg-red-900/50 text-red-300'}`}>
                            {log.status === 'error' ? 'ERROR' : 'SUCCESS'}
                        </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4 mb-6 text-sm">
                        <div className="p-3 bg-white/5 rounded border border-border">
                            <label className="text-muted block text-xs mb-1">Request ID</label>
                            <div className="font-mono text-xs break-all">{log.request_id}</div>
                        </div>
                        <div className="p-3 bg-white/5 rounded border border-border">
                            <label className="text-muted block text-xs mb-1">Timestamp</label>
                            <div className="font-mono text-xs">{log.time}</div>
                        </div>
                        <div className="p-3 bg-white/5 rounded border border-border">
                            <label className="text-muted block text-xs mb-1">Duration</label>
                            <div className="font-mono">{log.duration_ms} ms</div>
                        </div>
                        <div className="p-3 bg-white/5 rounded border border-border">
                            <label className="text-muted block text-xs mb-1">Mapping ID</label>
                            <div className="font-mono text-xs">{log.mapping_id}</div>
                        </div>
                    </div>

                    {log.error && (
                        <div className="mb-6">
                            <label className="text-muted block text-xs mb-2 font-bold uppercase tracking-wider">Error Message</label>
                            <div className="p-3 bg-red-900/10 border border-red-900/30 rounded font-mono text-sm text-red-300 whitespace-pre-wrap">
                                {log.error}
                            </div>
                        </div>
                    )}

                    {log.params && (
                        <div className="mb-6">
                            <label className="text-muted block text-xs mb-2 font-bold uppercase tracking-wider">Parameters</label>
                            <pre className="p-3 bg-black/30 rounded text-xs font-mono overflow-auto border border-border">
                                {JSON.stringify(log.params, null, 2)}
                            </pre>
                        </div>
                    )}

                    {log.stack && (
                        <div className="mb-4">
                            <label className="text-muted block text-xs mb-2 font-bold uppercase tracking-wider">Stack Trace</label>
                            <pre className="p-3 bg-black/30 rounded text-xs font-mono overflow-auto max-h-96 border border-border text-gray-400">
                                {log.stack}
                            </pre>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

const divWrapper = ({ children }) => <div>{children}</div>
