
const API_BASE = '/admin';

export const getHeaders = () => {
    const key = localStorage.getItem('admin_key') || '';
    return {
        'Content-Type': 'application/json',
        ...(key ? { 'X-API-Key': key } : {})
    };
};

export const fetchJson = async (path, options = {}) => {
    const res = await fetch(`${API_BASE}${path}`, {
        ...options,
        headers: { ...getHeaders(), ...options.headers }
    });

    // Handle auth errors (update global state if possible, or just throw)
    if (res.status === 401 || res.status === 403) {
        // trigger auth event or something
        window.dispatchEvent(new CustomEvent('auth-error', { detail: res.status }));
    }

    if (!res.ok) {
        const text = await res.text().catch(() => '');
        let errorMsg = text;
        try {
            const json = JSON.parse(text);
            errorMsg = json.detail || json.message || text;
        } catch (e) {
            // ignore
        }
        throw new Error(errorMsg || `Request failed: ${res.status}`);
    }
    return res.json();
};
