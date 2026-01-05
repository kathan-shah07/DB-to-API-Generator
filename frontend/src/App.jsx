import { useState, useEffect } from 'react';
import { Database, FileSearch, Code, Play, Terminal, Lock } from 'lucide-react';
import { Connectors } from './components/Connectors';
import { Schema } from './components/Schema';
import { Queries } from './components/Queries';
import { Mappings } from './components/Mappings';
import { Logs } from './components/Logs';
import { fetchJson } from './api';

export default function App() {
  const [activeTab, setActiveTab] = useState('connectors');
  const [adminKey, setAdminKey] = useState(localStorage.getItem('admin_key') || '');
  const [authStatus, setAuthStatus] = useState('unknown');

  useEffect(() => {
    const checkAuth = async () => {
      try {
        await fetchJson('/connectors');
        setAuthStatus('ok');
      } catch (e) {
        setAuthStatus('error');
      }
    };
    if (adminKey) checkAuth();
  }, [adminKey]);

  const saveKey = (key) => {
    localStorage.setItem('admin_key', key);
    setAdminKey(key);
    // trigger re-check
    setTimeout(() => {
      fetchJson('/connectors').then(() => setAuthStatus('ok')).catch(() => setAuthStatus('error'));
    }, 100);
  };

  const renderContent = () => {
    switch (activeTab) {
      case 'connectors': return <Connectors />;
      case 'schema': return <Schema />;
      case 'queries': return <Queries />;
      case 'mappings': return <Mappings />;
      case 'logs': return <Logs />;
      default: return <Connectors />;
    }
  };

  return (
    <div className="layout">
      <aside className="sidebar">
        <h1 className="text-xl font-bold mb-6 flex items-center gap-2 text-blue-400">
          <Database className="text-accent" /> DB API
        </h1>
        <nav className="flex col gap-2">
          <NavItem id="connectors" icon={<Database size={18} />} label="Connectors" active={activeTab} set={setActiveTab} />
          <NavItem id="schema" icon={<FileSearch size={18} />} label="Schema" active={activeTab} set={setActiveTab} />
          <NavItem id="queries" icon={<Code size={18} />} label="Queries" active={activeTab} set={setActiveTab} />
          <NavItem id="mappings" icon={<Play size={18} />} label="Mappings" active={activeTab} set={setActiveTab} />
          <NavItem id="logs" icon={<Terminal size={18} />} label="Logs" active={activeTab} set={setActiveTab} />
        </nav>

        <div className="mt-auto pt-4 border-t border-gray-700">
          <label className="text-xs text-muted mb-1 block flex items-center gap-1"><Lock size={10} /> Admin Key</label>
          <div className="flex gap-2">
            <input
              type="password"
              value={adminKey}
              onChange={e => setAdminKey(e.target.value)}
              className="text-xs"
              placeholder="Key..."
            />
            <button className="text-xs px-2" onClick={() => saveKey(adminKey)}>Save</button>
          </div>
          <div className="text-xs mt-1 text-muted">
            Status: <span className={authStatus === 'ok' ? 'text-green-400' : 'text-red-400'}>{authStatus}</span>
          </div>
        </div>
      </aside>
      <main className="main-content">
        {renderContent()}
      </main>
    </div>
  );
}

function NavItem({ id, icon, label, active, set }) {
  return (
    <button
      className={`nav-item ${active === id ? 'active' : ''}`}
      onClick={() => set(id)}
    >
      {icon}
      <span>{label}</span>
    </button>
  )
}
