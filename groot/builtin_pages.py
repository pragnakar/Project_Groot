"""Groot built-in pages — dashboard and artifact browser registered at startup."""

import logging

from groot.artifact_store import ArtifactStore

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Dashboard JSX — fetches /api/system/state and /api/pages
# ---------------------------------------------------------------------------

_DASHBOARD_JSX = """\
function Dropdown({ items }) {
  const [open, setOpen] = React.useState(false);
  const [hovered, setHovered] = React.useState(null);
  const ref = React.useRef(null);

  React.useEffect(() => {
    if (!open) return;
    const handler = e => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  return (
    <div ref={ref} style={{position:'relative', display:'inline-block', flexShrink:0}}>
      <button
        onClick={() => setOpen(o => !o)}
        style={{padding:'.25rem .65rem', fontSize:'.78rem', borderRadius:4, border:'1px solid #30363d', cursor:'pointer', background:'#21262d', color:'#8b949e'}}
      >
        Actions ▾
      </button>
      {open && (
        <div style={{position:'absolute', top:'100%', left:0, zIndex:200, background:'#161b22', border:'1px solid #30363d', borderRadius:6, minWidth:160, marginTop:2, boxShadow:'0 4px 12px rgba(0,0,0,.5)'}}>
          {items.map((item, i) => (
            <button
              key={i}
              onMouseEnter={() => setHovered(i)}
              onMouseLeave={() => setHovered(null)}
              onClick={() => { setOpen(false); item.onClick(); }}
              style={{display:'block', width:'100%', textAlign:'left', padding:'.4rem .75rem', background: hovered === i ? '#30363d' : 'transparent', border:'none', cursor:'pointer', color: item.danger ? '#ff6b6b' : '#e2e8f0', fontSize:'.82rem'}}
            >
              {item.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function Page() {
  const [state, setState]     = React.useState(null);
  const [pages, setPages]     = React.useState([]);
  const [events, setEvents]   = React.useState([]);
  const [apps, setApps]       = React.useState([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError]     = React.useState(null);
  const [apiKey, setApiKey]   = React.useState(() => sessionStorage.getItem('groot_key') || '');
  const [keyStatus, setKeyStatus] = React.useState('idle');
  const [importFile, setImportFile]     = React.useState(null);
  const [importing, setImporting]       = React.useState(false);
  const [importMsg, setImportMsg]       = React.useState(null);
  const [deleteStatus, setDeleteStatus]         = React.useState({});
  const [confirmDelete, setConfirmDelete]       = React.useState(null);
  const [pageDeleteStatus, setPageDeleteStatus] = React.useState({});
  const [confirmDeletePage, setConfirmDeletePage] = React.useState(null);
  const [pageSearch, setPageSearch] = React.useState('');
  const [toast, setToast] = React.useState(null);

  const showToast = (msg, ok) => {
    setToast({ msg, ok });
    setTimeout(() => setToast(null), 4000);
  };

  const saveKey = k => {
    setApiKey(k);
    sessionStorage.setItem('groot_key', k);
    setKeyStatus('idle');
  };

  React.useEffect(() => {
    if (!apiKey) { setKeyStatus('empty'); return; }
    setKeyStatus('validating');
    const t = setTimeout(() => {
      fetch('/api/system/state', {headers: {'X-Groot-Key': apiKey}})
        .then(r => setKeyStatus(r.ok ? 'ok' : 'fail'))
        .catch(() => setKeyStatus('fail'));
    }, 600);
    return () => clearTimeout(t);
  }, [apiKey]);

  const reload = () => {
    setLoading(true);
    Promise.all([
      fetch('/api/system/state', {headers: apiKey ? {'X-Groot-Key': apiKey} : {}}).then(r => r.ok ? r.json() : null),
      fetch('/api/pages').then(r => r.ok ? r.json() : []),
      fetch('/api/system/artifacts', {headers: apiKey ? {'X-Groot-Key': apiKey} : {}}).then(r => r.ok ? r.json() : null),
      fetch('/api/apps').then(r => r.ok ? r.json() : {apps:[]}),
    ])
      .then(([sysState, pageList, artifacts, appsData]) => {
        setState(sysState);
        setPages(pageList || []);
        setEvents(artifacts ? (artifacts.recent_events || []).slice(0, 10) : []);
        setApps((appsData && appsData.apps) || []);
        setLoading(false);
      })
      .catch(e => { setError(e.message); setLoading(false); });
  };

  React.useEffect(() => { reload(); }, []);

  const doDelete = (name, force) => {
    setDeleteStatus(s => ({...s, [name]: 'deleting\u2026'}));
    fetch('/api/apps/' + name + '?force=' + force, {
      method: 'DELETE',
      headers: {'X-Groot-Key': apiKey},
    })
      .then(r => r.json())
      .then(d => {
        if (d.detail) setDeleteStatus(s => ({...s, [name]: '\u2717 ' + d.detail}));
        else { setDeleteStatus(s => ({...s, [name]: '\u2713 deleted'})); reload(); }
      })
      .catch(e => setDeleteStatus(s => ({...s, [name]: '\u2717 ' + e.message})));
    setConfirmDelete(null);
  };

  const doDeletePage = name => {
    setPageDeleteStatus(s => ({...s, [name]: 'deleting\u2026'}));
    fetch('/api/tools/delete_page', {
      method: 'POST',
      headers: {'X-Groot-Key': apiKey, 'Content-Type': 'application/json'},
      body: JSON.stringify({name}),
    })
      .then(r => r.json())
      .then(d => {
        if (d.error || d.detail) setPageDeleteStatus(s => ({...s, [name]: '\u2717 ' + (d.detail || d.error)}));
        else { setPageDeleteStatus(s => ({...s, [name]: '\u2713 deleted'})); reload(); }
      })
      .catch(e => setPageDeleteStatus(s => ({...s, [name]: '\u2717 ' + e.message})));
    setConfirmDeletePage(null);
  };

  const doImport = () => {
    if (!importFile) return;
    setImporting(true);
    setImportMsg(null);
    const fd = new FormData();
    fd.append('file', importFile);
    fetch('/api/apps/import', { method:'POST', headers:{'X-Groot-Key': apiKey}, body: fd })
      .then(r => r.json())
      .then(d => {
        setImporting(false);
        if (d.detail) {
          setImportMsg({ ok: false, text: d.detail });
          showToast(d.detail, false);
        } else {
          const msg = '\u2713 ' + d.name + ' loaded \u2014 tools:' + d.tools_registered + ' pages:' + d.pages_registered;
          setImportMsg({ ok: true, text: msg });
          showToast(msg, true);
          reload();
        }
      })
      .catch(e => {
        setImporting(false);
        setImportMsg({ ok: false, text: e.message });
        showToast(e.message, false);
      });
  };

  const keyDot = () => {
    if (keyStatus === 'ok')         return <span style={{marginLeft:6, display:'inline-block', width:10, height:10, borderRadius:'50%', background:'#4ade80', verticalAlign:'middle'}} title="Key valid"></span>;
    if (keyStatus === 'fail')       return <span style={{marginLeft:6, display:'inline-block', width:10, height:10, borderRadius:'50%', background:'#ff6b6b', verticalAlign:'middle'}} title="Key invalid"></span>;
    if (keyStatus === 'empty')      return <span style={{marginLeft:6, display:'inline-block', width:10, height:10, borderRadius:'50%', background:'#4a5568', verticalAlign:'middle'}} title="No key set"></span>;
    if (keyStatus === 'validating') return <span style={{marginLeft:6, fontSize:'.75rem', color:'#8b949e'}}>...</span>;
    return null;
  };

  const s = {
    card:     { background:'#161b22', border:'1px solid #30363d', borderRadius:8, padding:'1.25rem', marginBottom:'1rem' },
    h1:       { fontSize:'1.5rem', fontWeight:600, color:'#e2e8f0', marginBottom:'1rem' },
    h2:       { fontSize:'.8rem', fontWeight:600, color:'#8b949e', marginBottom:'.75rem', textTransform:'uppercase', letterSpacing:'.08em' },
    row:      { display:'flex', justifyContent:'space-between', alignItems:'center', padding:'.4rem 0', borderBottom:'1px solid #21262d' },
    link:     { color:'#6366f1', textDecoration:'none', fontSize:'.9rem' },
    grid:     { display:'grid', gridTemplateColumns:'repeat(auto-fit, minmax(140px, 1fr))', gap:'1rem', marginBottom:'1rem' },
    statCard: { background:'#161b22', border:'1px solid #30363d', borderRadius:8, padding:'1rem', textAlign:'center' },
    bigNum:   { fontSize:'1.8rem', fontWeight:700, color:'#4ade80' },
    bigLabel: { color:'#8b949e', fontSize:'.8rem', marginTop:'.2rem' },
    two:      { display:'grid', gridTemplateColumns:'1fr 1fr', gap:'1rem' },
    eventRow: { padding:'.35rem 0', borderBottom:'1px solid #21262d', fontSize:'.85rem' },
    btn:      { padding:'.25rem .65rem', fontSize:'.78rem', borderRadius:4, border:'1px solid #30363d', cursor:'pointer', background:'#21262d', color:'#8b949e', marginLeft:'.35rem' },
    btnRed:   { padding:'.25rem .65rem', fontSize:'.78rem', borderRadius:4, border:'1px solid #ff6b6b', cursor:'pointer', background:'#21262d', color:'#ff6b6b', marginLeft:'.35rem' },
    btnGreen: { padding:'.25rem .65rem', fontSize:'.78rem', borderRadius:4, border:'1px solid #4ade80', cursor:'pointer', background:'#21262d', color:'#4ade80', marginLeft:'.35rem' },
    badge:    ok => ({ display:'inline-block', padding:'.1rem .45rem', borderRadius:4, fontSize:'.7rem', fontWeight:600,
                       background: ok ? '#0d2318' : '#2d1515', color: ok ? '#4ade80' : '#ff6b6b', marginRight:'.5rem' }),
    input:    { background:'#0d1117', border:'1px solid #30363d', borderRadius:4, padding:'.3rem .6rem', color:'#e2e8f0', fontSize:'.85rem', boxSizing:'border-box' },
    overlay:  { position:'fixed', inset:0, background:'rgba(0,0,0,.6)', display:'flex', alignItems:'center', justifyContent:'center', zIndex:100 },
    modal:    { background:'#161b22', border:'1px solid #30363d', borderRadius:8, padding:'1.5rem', minWidth:320, maxWidth:420 },
    tagSystem:  { display:'inline-block', padding:'.05rem .35rem', borderRadius:3, fontSize:'.65rem', fontWeight:600, background:'#21262d', color:'#6e7681', marginLeft:'.4rem', verticalAlign:'middle' },
    tagExample: { display:'inline-block', padding:'.05rem .35rem', borderRadius:3, fontSize:'.65rem', fontWeight:600, background:'#2d2208', color:'#d29922', marginLeft:'.4rem', verticalAlign:'middle' },
    spinner:  { display:'inline-block', width:12, height:12, border:'2px solid #4ade8040', borderTopColor:'#4ade80', borderRadius:'50%', animation:'spin 0.7s linear infinite', marginRight:6 },
  };

  const isSystemPage  = name => name.startsWith('groot-');
  const isExamplePage = name => name.startsWith('_');

  const filteredPages = pages.filter(p => {
    if (!pageSearch) return true;
    const q = pageSearch.toLowerCase();
    return p.name.toLowerCase().includes(q) || (p.description || '').toLowerCase().includes(q);
  });

  if (loading) return <div style={{color:'#8b949e', padding:'3rem 0', textAlign:'center'}}>Loading dashboard\u2026</div>;
  if (error)   return <div style={{color:'#ff6b6b', padding:'1rem'}}>Error: {error}</div>;

  const levelColor = l => l === 'error' ? '#ff6b6b' : l === 'warn' ? '#f0a854' : '#8b949e';

  return (
    <div>
      <style>{'@keyframes spin { to { transform: rotate(360deg) } }'}</style>

      {toast && (
        <div style={{position:'fixed', bottom:24, right:24, zIndex:300, background:'#161b22', border:'1px solid ' + (toast.ok ? '#4ade80' : '#ff6b6b'), borderRadius:8, padding:'.75rem 1rem', color: toast.ok ? '#4ade80' : '#ff6b6b', fontSize:'.85rem', maxWidth:360, boxShadow:'0 4px 16px rgba(0,0,0,.5)'}}>
          {toast.msg}
        </div>
      )}

      {confirmDelete && (
        <div style={s.overlay}>
          <div style={s.modal}>
            <div style={{color:'#e2e8f0', marginBottom:'1rem', fontWeight:600}}>Delete app "{confirmDelete}"?</div>
            <div style={{color:'#8b949e', fontSize:'.85rem', marginBottom:'1.25rem'}}>
              Removes all tools and pages. Force also deletes the directory on disk.
            </div>
            <div style={{display:'flex', gap:'.5rem', justifyContent:'flex-end'}}>
              <button style={s.btn} onClick={() => setConfirmDelete(null)}>Cancel</button>
              <button style={s.btn} onClick={() => doDelete(confirmDelete, false)}>Delete</button>
              <button style={s.btnRed} onClick={() => doDelete(confirmDelete, true)}>Force Delete</button>
            </div>
          </div>
        </div>
      )}

      {confirmDeletePage && (
        <div style={s.overlay}>
          <div style={s.modal}>
            <div style={{color:'#e2e8f0', marginBottom:'1rem', fontWeight:600}}>Delete page "{confirmDeletePage}"?</div>
            <div style={{color:'#8b949e', fontSize:'.85rem', marginBottom:'1.25rem'}}>
              This removes the page and its JSX from the store. The route will stop working immediately.
            </div>
            <div style={{display:'flex', gap:'.5rem', justifyContent:'flex-end'}}>
              <button style={s.btn} onClick={() => setConfirmDeletePage(null)}>Cancel</button>
              <button style={s.btnRed} onClick={() => doDeletePage(confirmDeletePage)}>Delete</button>
            </div>
          </div>
        </div>
      )}

      <h1 style={s.h1}><span style={{color:'#4ade80'}}>Groot</span> Dashboard <span style={{fontSize:'0.75rem', color:'#8b949e', fontWeight:'normal', marginLeft:'0.5rem'}}>v0.2.0</span></h1>

      {state && (
        <div style={s.grid}>
          <div style={s.statCard}><div style={s.bigNum}>{state.artifact_count}</div><div style={s.bigLabel}>Artifacts</div></div>
          <div style={s.statCard}><div style={s.bigNum}>{state.page_count}</div><div style={s.bigLabel}>Pages</div></div>
          <div style={s.statCard}><div style={s.bigNum}>{state.blob_count}</div><div style={s.bigLabel}>Blobs</div></div>
          <div style={s.statCard}><div style={s.bigNum}>{state.schema_count}</div><div style={s.bigLabel}>Schemas</div></div>
          <div style={s.statCard}><div style={{...s.bigNum, fontSize:'1.3rem'}}>{Math.floor(state.uptime_seconds)}s</div><div style={s.bigLabel}>Uptime</div></div>
          <div style={s.statCard}><div style={s.bigNum}>{apps.length}</div><div style={s.bigLabel}>Apps</div></div>
        </div>
      )}

      <div style={s.card}>
        <div style={s.h2}>App Manager</div>

        <div style={{display:'flex', gap:'.5rem', alignItems:'center', flexWrap:'wrap', marginBottom:'.5rem', paddingBottom:'1rem', borderBottom:'1px solid #21262d'}}>
          <input type="file" accept=".zip" onChange={e => setImportFile(e.target.files[0])}
            style={{color:'#8b949e', fontSize:'.85rem', flex:1, minWidth:180}} />
          <div style={{display:'flex', alignItems:'center'}}>
            <input style={{...s.input, width:200}} type="password" placeholder="API key"
              value={apiKey} onChange={e => saveKey(e.target.value)} />
            {keyDot()}
          </div>
          <button style={{...s.btnGreen, display:'flex', alignItems:'center'}} onClick={doImport} disabled={!importFile || importing}>
            {importing && <span style={s.spinner}></span>}
            {importing ? 'Installing\u2026' : 'Import ZIP'}
          </button>
        </div>
        {importMsg && (
          <div style={{marginBottom:'.75rem', fontSize:'.82rem', color: importMsg.ok ? '#4ade80' : '#ff6b6b'}}>
            {importMsg.text}
          </div>
        )}

        {apps.length === 0
          ? <div style={{color:'#8b949e', fontSize:'.9rem'}}>No apps loaded.</div>
          : apps.map(a => (
              <div key={a.name} style={{...s.row, gap:'.75rem'}}>
                <Dropdown items={[
                  { label: 'Export ZIP',    onClick: () => { window.location.href = '/api/apps/' + a.name + '/export'; } },
                  { label: 'Export + Data', onClick: () => { window.location.href = '/api/apps/' + a.name + '/export?include_data=true'; } },
                  { label: 'Delete\u2026',  onClick: () => setConfirmDelete(a.name), danger: true },
                ]} />
                <div style={{display:'flex', alignItems:'center', flex:1, minWidth:0}}>
                  <span style={s.badge(a.status === 'loaded')}>{a.status}</span>
                  <span style={{color:'#e2e8f0', fontWeight:600, fontSize:'.9rem'}}>{a.name}</span>
                  <span style={{color:'#8b949e', fontSize:'.78rem', marginLeft:'.5rem', overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap'}}>
                    {a.tools_count}t \u00b7 {a.pages_count}p{a.description ? ' \u00b7 ' + a.description : ''}
                  </span>
                </div>
                {deleteStatus[a.name] && <span style={{color:'#8b949e', fontSize:'.75rem', flexShrink:0}}>{deleteStatus[a.name]}</span>}
              </div>
            ))
        }
      </div>

      <div style={s.card}>
        <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:'.75rem'}}>
          <div style={s.h2}>Registered Pages</div>
          <input
            style={{...s.input, width:160, fontSize:'.78rem', padding:'.2rem .5rem'}}
            placeholder="Search pages\u2026"
            value={pageSearch}
            onChange={e => setPageSearch(e.target.value)}
          />
        </div>
        {filteredPages.length === 0
          ? <div style={{color:'#8b949e', fontSize:'.9rem'}}>{pageSearch ? "No pages match '" + pageSearch + "'" : 'No pages registered yet.'}</div>
          : filteredPages.map(p => {
              const isSys = isSystemPage(p.name);
              const isEx  = isExamplePage(p.name);
              const dropItems = [
                { label: 'Open',        onClick: () => { window.location.hash = '/apps/' + p.name; } },
                { label: 'View Source', onClick: () => window.open('/api/pages/' + p.name + '/source', '_blank') },
              ];
              if (!isSys) dropItems.push({ label: 'Delete\u2026', onClick: () => setConfirmDeletePage(p.name), danger: true });
              return (
                <div key={p.name} style={{...s.row, gap:'.75rem', flexWrap:'wrap', alignItems:'flex-start', paddingTop:'.5rem', paddingBottom:'.5rem'}}>
                  <Dropdown items={dropItems} />
                  <div style={{flex:1, minWidth:0}}>
                    <div style={{display:'flex', alignItems:'center', flexWrap:'wrap', gap:'.2rem'}}>
                      <a href={'#/apps/' + p.name} style={{...s.link, wordBreak:'break-all'}}>{p.name}</a>
                      {isSys && <span style={s.tagSystem}>system</span>}
                      {isEx  && <span style={s.tagExample}>example</span>}
                    </div>
                    <div
                      title={p.description || ''}
                      style={{color: p.description ? '#8b949e' : '#4a5568', fontStyle: p.description ? 'normal' : 'italic', fontSize:'.75rem', marginTop:'.15rem', overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap'}}
                    >
                      {p.description || 'No description'}
                    </div>
                    {pageDeleteStatus[p.name] && <div style={{color:'#8b949e', fontSize:'.75rem', marginTop:'.15rem'}}>{pageDeleteStatus[p.name]}</div>}
                  </div>
                </div>
              );
            })
        }
      </div>

      {events.length > 0 && (
        <div style={s.card}>
          <div style={s.h2}>Recent Events</div>
          {events.map(e => (
            <div key={e.id} style={s.eventRow}>
              <span style={{color: levelColor(e.level), marginRight:'.5rem', fontWeight:600}}>[{e.level}]</span>
              <span style={{color:'#e2e8f0'}}>{e.message}</span>
              <span style={{color:'#8b949e', fontSize:'.75rem', marginLeft:'.75rem'}}>{e.timestamp}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
"""

# ---------------------------------------------------------------------------
# Artifact browser JSX — tabs for Pages / Blobs / Schemas / Events
# ---------------------------------------------------------------------------

_ARTIFACTS_JSX = """\
function Page() {
  const [tab, setTab] = React.useState('pages');
  const [data, setData] = React.useState({ blobs: [], schemas: [], recent_events: [] });
  const [pages, setPages] = React.useState([]);
  const [selected, setSelected] = React.useState(null);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    Promise.all([
      fetch('/api/system/artifacts').then(r => r.ok ? r.json() : null),
      fetch('/api/pages').then(r => r.ok ? r.json() : []),
    ])
      .then(([artifacts, pageList]) => {
        if (artifacts) setData(artifacts);
        setPages(pageList || []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const s = {
    tabs:     { display:'flex', gap:'.25rem', marginBottom:'1rem', borderBottom:'1px solid #30363d', paddingBottom:'.5rem' },
    tab:      { padding:'.35rem .9rem', borderRadius:6, border:'1px solid #30363d', background:'#161b22', color:'#8b949e', cursor:'pointer', fontSize:'.9rem' },
    tabA:     { padding:'.35rem .9rem', borderRadius:6, border:'1px solid #4ade80', background:'#0d2318', color:'#4ade80', cursor:'pointer', fontSize:'.9rem', fontWeight:600 },
    card:     { background:'#161b22', border:'1px solid #30363d', borderRadius:8, padding:'1.25rem', marginBottom:'.6rem' },
    row:      { display:'flex', justifyContent:'space-between', alignItems:'center', padding:'.35rem 0', borderBottom:'1px solid #21262d', fontSize:'.875rem' },
    key:      { color:'#e2e8f0', fontFamily:'monospace' },
    meta:     { color:'#8b949e', fontSize:'.8rem' },
    pre:      { background:'#0d1117', border:'1px solid #30363d', borderRadius:6, padding:'1rem', fontSize:'.8rem', color:'#4ade80', whiteSpace:'pre-wrap', wordBreak:'break-all', marginTop:'.75rem', maxHeight:300, overflow:'auto' },
    levelColor: l => l === 'error' ? '#ff6b6b' : l === 'warn' ? '#f0a854' : '#8b949e',
    h1:       { fontSize:'1.5rem', fontWeight:600, color:'#e2e8f0', marginBottom:'1rem' },
    empty:    { color:'#8b949e', fontSize:'.9rem', padding:'1rem 0' },
    link:     { color:'#6366f1', textDecoration:'none', fontSize:'.9rem' },
    btn:      { marginTop:'.5rem', padding:'.25rem .6rem', fontSize:'.8rem', cursor:'pointer', background:'#21262d', border:'1px solid #30363d', borderRadius:4 },
  };

  const blobs   = data.blobs || [];
  const schemas = data.schemas || [];
  const events  = data.recent_events || [];

  if (loading) return <div style={{color:'#8b949e', padding:'3rem 0', textAlign:'center'}}>Loading artifacts\u2026</div>;

  return (
    <div>
      <h1 style={s.h1}>Artifact Browser</h1>

      <div style={s.tabs}>
        <button style={tab === 'pages'   ? s.tabA : s.tab} onClick={() => { setTab('pages');   setSelected(null); }}>Pages ({pages.length})</button>
        <button style={tab === 'blobs'   ? s.tabA : s.tab} onClick={() => { setTab('blobs');   setSelected(null); }}>Blobs ({blobs.length})</button>
        <button style={tab === 'schemas' ? s.tabA : s.tab} onClick={() => { setTab('schemas'); setSelected(null); }}>Schemas ({schemas.length})</button>
        <button style={tab === 'events'  ? s.tabA : s.tab} onClick={() => { setTab('events');  setSelected(null); }}>Events ({events.length})</button>
      </div>

      {tab === 'pages' && (
        <div>
          {pages.length === 0
            ? <div style={s.empty}>No pages registered.</div>
            : pages.map(p => (
                <div key={p.name} style={s.card}>
                  <div style={s.row}>
                    <div style={{display:'flex', flexDirection:'column', gap:'.2rem', flex:1, minWidth:0}}>
                      <a href={'#/apps/' + p.name} style={s.link}>{p.name}</a>
                      <span
                        title={p.description || ''}
                        style={{color: p.description ? '#8b949e' : '#4a5568', fontStyle: p.description ? 'normal' : 'italic', fontSize:'.78rem', overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap'}}
                      >
                        {p.description || 'No description'}
                      </span>
                    </div>
                    <span style={{color:'#8b949e', fontSize:'.75rem', whiteSpace:'nowrap', marginLeft:'1rem'}}>{p.created_at || ''}</span>
                  </div>
                  <div style={{display:'flex', gap:'.5rem', marginTop:'.5rem'}}>
                    <button style={{...s.btn, color:'#6366f1', borderColor:'#6366f1'}} onClick={() => { window.location.hash = '/apps/' + p.name; }}>Open</button>
                    <button style={{...s.btn, color:'#8b949e'}} onClick={() => window.open('/api/pages/' + p.name + '/source', '_blank')}>Source</button>
                  </div>
                </div>
              ))
          }
        </div>
      )}

      {tab === 'blobs' && (
        <div>
          {blobs.length === 0
            ? <div style={s.empty}>No blobs stored.</div>
            : blobs.map(b => (
                <div key={b.key} style={s.card}>
                  <div style={s.row}>
                    <span style={s.key}>{b.key}</span>
                    <span style={s.meta}>{b.content_type} \u00b7 {b.size_bytes}B \u00b7 {b.created_at}</span>
                  </div>
                  {selected === b.key
                    ? <div><pre style={s.pre}>{b.data || '(content not loaded \u2014 use /api/tools/read_blob)'}</pre>
                        <button onClick={() => setSelected(null)} style={{...s.btn, color:'#e2e8f0'}}>Close</button>
                      </div>
                    : <button onClick={() => setSelected(b.key)} style={{...s.btn, color:'#8b949e'}}>Inspect</button>
                  }
                </div>
              ))
          }
        </div>
      )}

      {tab === 'schemas' && (
        <div>
          {schemas.length === 0
            ? <div style={s.empty}>No schemas defined.</div>
            : schemas.map(sc => (
                <div key={sc.name} style={s.card}>
                  <div style={s.row}>
                    <span style={s.key}>{sc.name}</span>
                    <span style={s.meta}>{sc.created_at}</span>
                  </div>
                  {selected === sc.name
                    ? <div><pre style={s.pre}>{JSON.stringify(sc.definition || {}, null, 2)}</pre>
                        <button onClick={() => setSelected(null)} style={{...s.btn, color:'#e2e8f0'}}>Close</button>
                      </div>
                    : <button onClick={() => setSelected(sc.name)} style={{...s.btn, color:'#8b949e'}}>View Schema</button>
                  }
                </div>
              ))
          }
        </div>
      )}

      {tab === 'events' && (
        <div>
          {events.length === 0
            ? <div style={s.empty}>No events logged.</div>
            : events.map(e => (
                <div key={e.id} style={{...s.row, alignItems:'flex-start'}}>
                  <span style={{color: s.levelColor(e.level), marginRight:'.5rem', fontWeight:600, minWidth:50}}>[{e.level}]</span>
                  <span style={{color:'#e2e8f0', flex:1}}>{e.message}</span>
                  <span style={{color:'#8b949e', fontSize:'.75rem', marginLeft:'1rem', whiteSpace:'nowrap'}}>{e.timestamp}</span>
                </div>
              ))
          }
        </div>
      )}
    </div>
  );
}
"""


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

async def register_builtin_pages(store: ArtifactStore) -> None:
    """Upsert built-in pages into the artifact store at startup."""
    pages = [
        ("groot-dashboard", _DASHBOARD_JSX, "Groot system dashboard"),
        ("groot-artifacts", _ARTIFACTS_JSX, "Browse stored artifacts"),
    ]
    for name, jsx, description in pages:
        try:
            await store.create_page(name, jsx, description)
            logger.info("Registered built-in page: %s", name)
        except ValueError:
            await store.update_page(name, jsx)
            logger.info("Updated built-in page: %s", name)
