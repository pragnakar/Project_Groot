"""Groot built-in pages — dashboard and artifact browser registered at startup."""

import logging

from groot.artifact_store import ArtifactStore

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Dashboard JSX — fetches /api/system/state and /api/pages
# ---------------------------------------------------------------------------

_DASHBOARD_JSX = """\
function Page() {
  const [state, setState] = React.useState(null);
  const [pages, setPages] = React.useState([]);
  const [events, setEvents] = React.useState([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState(null);

  React.useEffect(() => {
    Promise.all([
      fetch('/api/system/state').then(r => r.ok ? r.json() : null),
      fetch('/api/pages').then(r => r.ok ? r.json() : []),
      fetch('/api/system/artifacts').then(r => r.ok ? r.json() : null),
    ])
      .then(([sysState, pageList, artifacts]) => {
        setState(sysState);
        setPages(pageList || []);
        setEvents(artifacts ? (artifacts.recent_events || []).slice(0, 10) : []);
        setLoading(false);
      })
      .catch(e => { setError(e.message); setLoading(false); });
  }, []);

  const s = {
    card:      { background:'#161b22', border:'1px solid #30363d', borderRadius:8, padding:'1.25rem', marginBottom:'1rem' },
    h1:        { fontSize:'1.5rem', fontWeight:600, color:'#e2e8f0', marginBottom:'1rem' },
    h2:        { fontSize:'.8rem', fontWeight:600, color:'#8b949e', marginBottom:'.75rem', textTransform:'uppercase', letterSpacing:'.08em' },
    row:       { display:'flex', justifyContent:'space-between', alignItems:'center', padding:'.4rem 0', borderBottom:'1px solid #21262d' },
    label:     { color:'#8b949e', fontSize:'.9rem' },
    val:       { color:'#4ade80', fontWeight:600 },
    link:      { color:'#6366f1', textDecoration:'none', fontSize:'.9rem' },
    grid:      { display:'grid', gridTemplateColumns:'repeat(auto-fit, minmax(140px, 1fr))', gap:'1rem', marginBottom:'1rem' },
    statCard:  { background:'#161b22', border:'1px solid #30363d', borderRadius:8, padding:'1rem', textAlign:'center' },
    bigNum:    { fontSize:'1.8rem', fontWeight:700, color:'#4ade80' },
    bigLabel:  { color:'#8b949e', fontSize:'.8rem', marginTop:'.2rem' },
    two:       { display:'grid', gridTemplateColumns:'1fr 1fr', gap:'1rem' },
    eventRow:  { padding:'.35rem 0', borderBottom:'1px solid #21262d', fontSize:'.85rem' },
  };

  if (loading) return <div style={{color:'#8b949e', padding:'3rem 0', textAlign:'center'}}>Loading dashboard…</div>;
  if (error)   return <div style={{color:'#ff6b6b', padding:'1rem'}}>Error: {error}</div>;

  const levelColor = l => l === 'error' ? '#ff6b6b' : l === 'warn' ? '#f0a854' : '#8b949e';

  return (
    <div>
      <h1 style={s.h1}><span style={{color:'#4ade80'}}>Groot</span> Dashboard <span style={{fontSize:'0.75rem', color:'#8b949e', fontWeight:'normal', marginLeft:'0.5rem'}}>v0.2.0</span></h1>

      {state && (
        <div style={s.grid}>
          <div style={s.statCard}><div style={s.bigNum}>{state.artifact_count}</div><div style={s.bigLabel}>Artifacts</div></div>
          <div style={s.statCard}><div style={s.bigNum}>{state.page_count}</div><div style={s.bigLabel}>Pages</div></div>
          <div style={s.statCard}><div style={s.bigNum}>{state.blob_count}</div><div style={s.bigLabel}>Blobs</div></div>
          <div style={s.statCard}><div style={s.bigNum}>{state.schema_count}</div><div style={s.bigLabel}>Schemas</div></div>
          <div style={s.statCard}><div style={{...s.bigNum, fontSize:'1.3rem'}}>{Math.floor(state.uptime_seconds)}s</div><div style={s.bigLabel}>Uptime</div></div>
        </div>
      )}

      <div style={s.two}>
        <div style={s.card}>
          <div style={s.h2}>Registered Pages</div>
          {pages.length === 0
            ? <div style={{color:'#8b949e', fontSize:'.9rem'}}>No pages registered yet.</div>
            : pages.map(p => (
                <div key={p.name} style={s.row}>
                  <a href={'#/apps/' + p.name} style={s.link}>{p.name}</a>
                  <span style={{color:'#8b949e', fontSize:'.75rem'}}>{p.description || ''}</span>
                </div>
              ))
          }
        </div>

        <div style={s.card}>
          <div style={s.h2}>Quick Links</div>
          <div style={{...s.row, borderBottom:'none', paddingBottom:'.25rem'}}>
            <a href="#/apps/groot-artifacts" style={s.link}>Artifact Browser →</a>
          </div>
          <div style={{...s.row, borderBottom:'none', paddingBottom:'.25rem'}}>
            <a href="/docs" style={s.link} target="_blank" rel="noreferrer">API Docs →</a>
          </div>
          <div style={{...s.row, borderBottom:'none', paddingBottom:'.25rem'}}>
            <a href="/health" style={s.link} target="_blank" rel="noreferrer">Health Check →</a>
          </div>
        </div>
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
# Artifact browser JSX — tabs for Blobs / Schemas / Events
# ---------------------------------------------------------------------------

_ARTIFACTS_JSX = """\
function Page() {
  const [tab, setTab] = React.useState('blobs');
  const [data, setData] = React.useState({ blobs: [], schemas: [], recent_events: [] });
  const [selected, setSelected] = React.useState(null);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    fetch('/api/system/artifacts')
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (d) setData(d); setLoading(false); })
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
  };

  const blobs   = data.blobs || [];
  const schemas = data.schemas || [];
  const events  = data.recent_events || [];

  if (loading) return <div style={{color:'#8b949e', padding:'3rem 0', textAlign:'center'}}>Loading artifacts…</div>;

  return (
    <div>
      <h1 style={s.h1}>Artifact Browser</h1>

      <div style={s.tabs}>
        <button style={tab === 'blobs'   ? s.tabA : s.tab} onClick={() => { setTab('blobs');   setSelected(null); }}>Blobs ({blobs.length})</button>
        <button style={tab === 'schemas' ? s.tabA : s.tab} onClick={() => { setTab('schemas'); setSelected(null); }}>Schemas ({schemas.length})</button>
        <button style={tab === 'events'  ? s.tabA : s.tab} onClick={() => { setTab('events');  setSelected(null); }}>Events ({events.length})</button>
      </div>

      {tab === 'blobs' && (
        <div>
          {blobs.length === 0
            ? <div style={s.empty}>No blobs stored.</div>
            : blobs.map(b => (
                <div key={b.key} style={s.card}>
                  <div style={s.row}>
                    <span style={s.key}>{b.key}</span>
                    <span style={s.meta}>{b.content_type} · {b.size_bytes}B · {b.created_at}</span>
                  </div>
                  {selected === b.key
                    ? <div><pre style={s.pre}>{b.data || '(content not loaded — use /api/tools/read_blob)'}</pre>
                        <button onClick={() => setSelected(null)} style={{marginTop:'.5rem', padding:'.25rem .6rem', fontSize:'.8rem', cursor:'pointer', background:'#21262d', border:'1px solid #30363d', color:'#e2e8f0', borderRadius:4}}>Close</button>
                      </div>
                    : <button onClick={() => setSelected(b.key)} style={{marginTop:'.5rem', padding:'.25rem .6rem', fontSize:'.8rem', cursor:'pointer', background:'#21262d', border:'1px solid #30363d', color:'#8b949e', borderRadius:4}}>Inspect</button>
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
                        <button onClick={() => setSelected(null)} style={{marginTop:'.5rem', padding:'.25rem .6rem', fontSize:'.8rem', cursor:'pointer', background:'#21262d', border:'1px solid #30363d', color:'#e2e8f0', borderRadius:4}}>Close</button>
                      </div>
                    : <button onClick={() => setSelected(sc.name)} style={{marginTop:'.5rem', padding:'.25rem .6rem', fontSize:'.8rem', cursor:'pointer', background:'#21262d', border:'1px solid #30363d', color:'#8b949e', borderRadius:4}}>View Schema</button>
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
