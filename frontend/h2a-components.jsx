/* hate2action — shared UI components */
const { useState, useEffect, useRef, useCallback } = React;

/* ── BUTTON ── */
function Button({ children, variant = 'primary', size = 'md', onClick, disabled, type = 'button', className = '' }) {
  const base = 'inline-flex items-center gap-2 font-semibold rounded-lg transition-all cursor-pointer border';
  const sizes = { sm: 'px-3 py-1.5 text-xs', md: 'px-4 py-2 text-sm', lg: 'px-6 py-3 text-base' };
  const variants = {
    primary: 'bg-coral text-white border-coral hover:bg-coral-dark',
    secondary: 'bg-navy text-white border-navy hover:bg-navy-dark',
    ghost: 'bg-transparent text-charcoal border-border hover:bg-sand-dark',
    teal: 'bg-teal text-white border-teal hover:opacity-90',
    danger: 'bg-transparent text-red-500 border-red-200 hover:bg-red-50',
    outline: 'bg-white text-navy border-border hover:border-navy',
  };
  return (
    <button type={type} className={`${base} ${sizes[size]} ${variants[variant]} ${disabled ? 'opacity-40 cursor-not-allowed' : ''} ${className}`}
      onClick={onClick} disabled={disabled}>
      {children}
    </button>
  );
}

/* ── INPUT ── */
function Input({ value, onChange, placeholder, type = 'text', className = '', ...rest }) {
  return (
    <input
      type={type}
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      className={`w-full px-3 py-2 text-sm bg-white border border-border rounded-lg outline-none focus:border-teal focus:ring-2 focus:ring-teal/20 transition-all placeholder:text-muted ${className}`}
      {...rest}
    />
  );
}

/* ── TEXTAREA ── */
function Textarea({ value, onChange, placeholder, rows = 4, className = '' }) {
  return (
    <textarea
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      rows={rows}
      className={`w-full px-3 py-2 text-sm bg-white border border-border rounded-lg outline-none focus:border-teal focus:ring-2 focus:ring-teal/20 transition-all placeholder:text-muted resize-vertical ${className}`}
    />
  );
}

/* ── SELECT ── */
function Select({ value, onChange, children, className = '' }) {
  return (
    <select value={value} onChange={onChange}
      className={`w-full px-3 py-2 text-sm bg-white border border-border rounded-lg outline-none focus:border-teal focus:ring-2 focus:ring-teal/20 transition-all ${className}`}>
      {children}
    </select>
  );
}

/* ── CARD ── */
function Card({ children, className = '', onClick }) {
  return (
    <div className={`bg-white rounded-xl border border-border shadow-sm ${onClick ? 'cursor-pointer hover:shadow-md hover:border-teal/40 transition-all' : ''} ${className}`}
      onClick={onClick}>
      {children}
    </div>
  );
}
function CardHeader({ children, className = '' }) {
  return <div className={`px-5 pt-5 pb-2 ${className}`}>{children}</div>;
}
function CardTitle({ children, className = '' }) {
  return <h3 className={`font-bold text-base text-charcoal leading-snug ${className}`}>{children}</h3>;
}
function CardDescription({ children, className = '' }) {
  return <p className={`text-sm text-muted mt-1 line-clamp-2 ${className}`}>{children}</p>;
}
function CardContent({ children, className = '' }) {
  return <div className={`px-5 pb-5 ${className}`}>{children}</div>;
}

/* ── BADGE ── */
function Badge({ children, variant = 'default' }) {
  const variants = {
    default: 'bg-sage/30 text-navy',
    coral: 'bg-coral/15 text-coral-dark',
    teal: 'bg-teal/15 text-teal-dark',
    navy: 'bg-navy/10 text-navy',
    yellow: 'bg-amber-100 text-amber-700',
    green: 'bg-emerald-100 text-emerald-700',
  };
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${variants[variant]}`}>
      {children}
    </span>
  );
}

/* ── PAGE HEADER ── */
function PageHeader({ title, subtitle, action }) {
  return (
    <div className="flex items-start justify-between mb-6">
      <div>
        <h1 className="text-2xl font-extrabold text-charcoal">{title}</h1>
        {subtitle && <p className="text-sm text-muted mt-1">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}

/* ── SEARCH BAR ── */
function SearchBar({ value, onChange, placeholder = 'Search…' }) {
  return (
    <div className="relative mb-5">
      <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
        <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
      </svg>
      <input value={value} onChange={onChange} placeholder={placeholder}
        className="w-full pl-9 pr-4 py-2 text-sm bg-white border border-border rounded-lg outline-none focus:border-teal focus:ring-2 focus:ring-teal/20 transition-all" />
    </div>
  );
}

/* ── EMPTY STATE ── */
function EmptyState({ icon, title, description, action }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="text-5xl mb-4">{icon}</div>
      <h3 className="font-bold text-charcoal text-lg">{title}</h3>
      {description && <p className="text-muted text-sm mt-1 max-w-xs">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

/* ── DETAIL ROW ── */
function DetailRow({ label, children }) {
  return (
    <div className="flex gap-4 py-3 border-b border-border last:border-0">
      <span className="text-sm font-semibold text-muted w-36 flex-shrink-0">{label}</span>
      <span className="text-sm text-charcoal flex-1">{children}</span>
    </div>
  );
}

/* ── FORM GROUP ── */
function FormGroup({ label, required, children, hint }) {
  return (
    <div className="mb-4">
      <label className="block text-xs font-bold text-muted uppercase tracking-wider mb-1.5">
        {label}{required && <span className="text-coral ml-0.5">*</span>}
      </label>
      {children}
      {hint && <p className="text-xs text-muted mt-1">{hint}</p>}
    </div>
  );
}

/* ── MODAL ── */
function Modal({ title, onClose, children, footer, width = 'max-w-lg' }) {
  useEffect(() => {
    const h = e => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', h);
    return () => window.removeEventListener('keydown', h);
  }, [onClose]);
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: 'rgba(31,58,95,0.5)', backdropFilter: 'blur(4px)' }}
      onClick={e => e.target === e.currentTarget && onClose()}>
      <div className={`bg-white rounded-2xl shadow-2xl w-full ${width} max-h-[90vh] overflow-y-auto`} style={{ animation: 'slideUp .2s ease' }}>
        <div className="flex items-center justify-between px-6 pt-5 pb-4 border-b border-border">
          <h2 className="font-bold text-lg text-charcoal">{title}</h2>
          <button onClick={onClose} className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-sand-dark text-muted text-xl transition-colors">×</button>
        </div>
        <div className="px-6 py-5">{children}</div>
        {footer && <div className="px-6 pb-5 flex justify-end gap-3 border-t border-border pt-4">{footer}</div>}
      </div>
    </div>
  );
}

/* ── CONFIRM DIALOG ── */
function ConfirmDialog({ message, onConfirm, onCancel }) {
  return (
    <Modal title="Confirm" onClose={onCancel} footer={<>
      <Button variant="ghost" onClick={onCancel}>Cancel</Button>
      <Button variant="danger" onClick={onConfirm}>Delete</Button>
    </>}>
      <p className="text-sm text-charcoal">{message}</p>
    </Modal>
  );
}

/* ── LOADING SPINNER ── */
function Spinner() {
  return (
    <div className="flex items-center justify-center py-16">
      <div className="w-8 h-8 border-2 border-border border-t-coral rounded-full" style={{ animation: 'spin 0.8s linear infinite' }} />
    </div>
  );
}

/* ── BACK BUTTON ── */
function BackButton({ onClick, label = 'Back' }) {
  return (
    <button onClick={onClick} className="inline-flex items-center gap-1.5 text-sm text-muted hover:text-charcoal transition-colors mb-5">
      <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M19 12H5M12 5l-7 7 7 7"/></svg>
      {label}
    </button>
  );
}

/* ── STAT CARD ── */
function StatCard({ label, value, icon, color = 'coral' }) {
  const colors = { coral: 'text-coral', teal: 'text-teal', navy: 'text-navy', sage: 'text-sage-dark' };
  return (
    <Card className="flex items-center gap-4 p-5">
      <div className={`text-3xl ${colors[color]}`}>{icon}</div>
      <div>
        <div className="text-2xl font-extrabold text-charcoal">{value}</div>
        <div className="text-xs text-muted font-semibold uppercase tracking-wider">{label}</div>
      </div>
    </Card>
  );
}

/* ── TOAST SYSTEM ── */
let _addToast = () => {};
function ToastProvider() {
  const [toasts, setToasts] = useState([]);
  _addToast = useCallback((msg, type = 'success') => {
    const id = Date.now();
    setToasts(t => [...t, { id, msg, type }]);
    setTimeout(() => setToasts(t => t.filter(x => x.id !== id)), 3500);
  }, []);
  if (!toasts.length) return null;
  return (
    <div style={{ position: 'fixed', bottom: 24, right: 24, zIndex: 200, display: 'flex', flexDirection: 'column', gap: 8 }}>
      {toasts.map(t => (
        <div key={t.id} style={{ padding: '10px 16px', borderRadius: 10, fontSize: 13, fontWeight: 600, maxWidth: 320,
          background: t.type === 'error' ? '#fee2e2' : t.type === 'info' ? '#e0f2fe' : '#dcfce7',
          color: t.type === 'error' ? '#b91c1c' : t.type === 'info' ? '#0369a1' : '#15803d',
          border: `1px solid ${t.type === 'error' ? '#fca5a5' : t.type === 'info' ? '#7dd3fc' : '#86efac'}`,
          boxShadow: '0 4px 12px rgba(0,0,0,0.1)', animation: 'slideUp .2s ease' }}>
          {t.msg}
        </div>
      ))}
    </div>
  );
}
function toast(msg, type) { _addToast(msg, type); }
toast.error = (msg) => _addToast(msg, 'error');
toast.info  = (msg) => _addToast(msg, 'info');

/* ── SETTINGS MODAL ── */
function SettingsModal({ onClose }) {
  const cfg = window.api.getConfig();
  const [baseURL, setBaseURL] = useState(cfg.baseURL || 'https://hate2action.devalma.com');
  const [apiKey, setApiKey]   = useState(cfg.apiKey  || '');
  const [status, setStatus]   = useState(null);

  async function testConnection() {
    setStatus('testing');
    window.api.saveConfig({ baseURL, apiKey });
    try {
      await window.api.getOrganizations();
      setStatus('ok');
    } catch (e) {
      setStatus('error:' + e.message);
    }
  }
  function save() {
    window.api.saveConfig({ baseURL, apiKey });
    toast('Settings saved — reload pages to apply');
    onClose();
  }
  return (
    <Modal title="⚙️ API Settings" onClose={onClose}
      footer={<><Button variant="ghost" onClick={onClose}>Cancel</Button><Button onClick={save}>Save</Button></>}>
      <FormGroup label="Backend URL" hint="Your FastAPI server base URL">
        <Input value={baseURL} onChange={e => setBaseURL(e.target.value)} placeholder="https://hate2action.devalma.com" />
      </FormGroup>
      <FormGroup label="API Key (X-API-Key)" hint="Leave blank if no auth is set">
        <Input value={apiKey} onChange={e => setApiKey(e.target.value)} placeholder="your-api-key" type="password" />
      </FormGroup>
      <button onClick={testConnection} className="text-sm text-teal hover:underline font-semibold mb-2">
        {status === 'testing' ? '⏳ Testing…' : status === 'ok' ? '✅ Connected!' : status?.startsWith('error') ? '❌ ' + status.slice(6) : '🔌 Test connection'}
      </button>
    </Modal>
  );
}

/* ── API ERROR BANNER ── */
function ApiErrorBanner({ error, onRetry }) {
  return (
    <div className="rounded-xl border border-red-200 bg-red-50 p-4 mb-5 flex items-start gap-3">
      <span className="text-red-500 text-xl">⚠️</span>
      <div className="flex-1">
        <p className="text-sm font-bold text-red-700">API error</p>
        <p className="text-xs text-red-500 mt-0.5">{error}</p>
      </div>
      {onRetry && <button onClick={onRetry} className="text-xs font-bold text-red-600 hover:underline">Retry</button>}
    </div>
  );
}

Object.assign(window, {
  Button, Input, Textarea, Select, Card, CardHeader, CardTitle, CardDescription, CardContent,
  Badge, PageHeader, SearchBar, EmptyState, DetailRow, FormGroup, Modal, ConfirmDialog,
  Spinner, BackButton, StatCard, ToastProvider, toast, SettingsModal, ApiErrorBanner,
});
