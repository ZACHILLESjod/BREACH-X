import { useCallback, useEffect, useMemo, useState } from 'react'
import { AnimatePresence, MotionConfig, motion } from 'framer-motion'
import { checkApi, getAssetExposure, getAssets } from './api.js'

function Icon({ name, size = 18 }) {
  const paths = {
    grid: <><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" /></>,
    boxes: <><path d="m12 3 9 5-9 5-9-5 9-5Z" /><path d="m3 12 9 5 9-5M3 16l9 5 9-5" /></>,
    shield: <><path d="M12 22s8-4 8-11V5l-8-3-8 3v6c0 7 8 11 8 11Z" /><path d="m9 12 2 2 4-4" /></>,
    activity: <><path d="M3 12h4l3-8 4 16 3-8h4" /></>,
    search: <><circle cx="11" cy="11" r="7" /><path d="m20 20-4-4" /></>,
    arrow: <><path d="M5 12h14M13 6l6 6-6 6" /></>,
    back: <><path d="m15 18-6-6 6-6" /><path d="M20 12H9" /></>,
    server: <><rect x="3" y="4" width="18" height="7" rx="2" /><rect x="3" y="13" width="18" height="7" rx="2" /><path d="M7 7.5h.01M7 16.5h.01M11 7.5h6M11 16.5h6" /></>,
    software: <><rect x="4" y="4" width="16" height="16" rx="3" /><path d="M9 9h6v6H9zM9 1v3m6-3v3M9 20v3m6-3v3M1 9h3m-3 6h3m16-6h3m-3 6h3" /></>,
    alert: <><path d="M10.3 3.9 2.4 17.5A1.7 1.7 0 0 0 3.9 20h16.2a1.7 1.7 0 0 0 1.5-2.5L13.7 3.9a2 2 0 0 0-3.4 0Z" /><path d="M12 9v4m0 3h.01" /></>,
    clock: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>,
    external: <><path d="M14 3h7v7m0-7-9 9" /><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" /></>,
    nodes: <><circle cx="5" cy="12" r="2.5" /><circle cx="19" cy="6" r="2.5" /><circle cx="19" cy="18" r="2.5" /><path d="m7.3 11 9.4-4M7.3 13l9.4 4" /></>,
    trend: <><path d="M3 17 9 11l4 4 8-9" /><path d="M16 6h5v5" /></>,
    globe: <><circle cx="12" cy="12" r="9" /><path d="M3 12h18M12 3c2.4 2.5 3.5 5.5 3.5 9S14.4 18.5 12 21c-2.4-2.5-3.5-5.5-3.5-9S9.6 5.5 12 3Z" /></>,
    target: <><circle cx="12" cy="12" r="8" /><circle cx="12" cy="12" r="3" /><path d="M12 2v2m0 16v2M2 12h2m16 0h2" /></>,
  }
  return <svg aria-hidden="true" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">{paths[name]}</svg>
}

function RiskBadge({ level = 'UNKNOWN' }) {
  return <span className={`risk-badge risk-${String(level).toLowerCase()}`}><span className="risk-dot" />{level}</span>
}

function MetricCard({ label, value, note, icon, tone = '' }) {
  return <article className="metric-card">
    <div className={`metric-icon ${tone}`}><Icon name={icon} /></div>
    <div className="metric-copy"><span className="eyebrow">{label}</span><strong><AnimatedValue value={value} /></strong><span className="metric-note">{note}</span></div>
  </article>
}

function EmptyState({ title, detail, action }) {
  return <div className="empty-state">
    <div className="empty-icon"><Icon name="boxes" size={23} /></div>
    <h3>{title}</h3><p>{detail}</p>{action}
  </div>
}

function LoadingState({ label = 'Loading exposure data…' }) {
  return <div className="loading-state"><span className="spinner" />{label}</div>
}

function AnimatedValue({ value, duration = 650 }) {
  const numeric = typeof value === 'number' && Number.isFinite(value)
  const [display, setDisplay] = useState(numeric ? 0 : value)
  useEffect(() => {
    if (!numeric || window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) {
      setDisplay(value)
      return undefined
    }
    let frame
    const started = performance.now()
    const tick = (now) => {
      const progress = Math.min(1, (now - started) / duration)
      setDisplay(Math.round(value * (1 - Math.pow(1 - progress, 3))))
      if (progress < 1) frame = requestAnimationFrame(tick)
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [duration, numeric, value])
  return <span className={numeric ? 'animated-value' : ''}>{display}</span>
}

function AssetLookup({ onLookup, loading, error, compact = false }) {
  const [assetId, setAssetId] = useState('')
  const submit = (event) => {
    event.preventDefault()
    if (assetId.trim()) onLookup(assetId.trim())
  }
  return <div className={`lookup-wrap ${compact ? 'lookup-compact' : ''}`}>
    <form className="lookup-form" onSubmit={submit}>
      <Icon name="search" size={19} />
      <input value={assetId} onChange={(event) => setAssetId(event.target.value)} placeholder="Enter an asset ID" aria-label="Asset ID" />
      <button className={`button button-primary ${loading ? 'is-loading' : ''}`} disabled={loading || !assetId.trim()}>{loading ? 'Loading…' : 'Load asset'}<Icon name="arrow" size={16} /></button>
    </form>
    {error && <div className="inline-error" role="alert"><Icon name="alert" size={16} />{error}</div>}
  </div>
}

function ExposureTable({ rows, showAsset = false, emptyTitle = 'No exposure checks yet' }) {
  if (!rows.length) return <EmptyState title={emptyTitle} detail="Load an asset to see its software and vulnerability assessments here." />
  return <div className="table-scroll"><table className="data-table">
    <thead><tr><th>CVE</th>{showAsset && <th>Asset</th>}<th>Software</th><th>Version</th><th>CVSS</th><th>Severity</th><th>Result</th><th>Risk</th></tr></thead>
    <tbody>{rows.map((row, index) => <tr key={`${row.asset_id || ''}-${row.software_id}-${row.cve_id}-${index}`}>
      <td><span className="cve-code">{row.cve_id}</span></td>
      {showAsset && <td>{row.asset_hostname || row.asset_id}</td>}
      <td className="software-cell"><strong>{row.affected_software}</strong><span>{row.vendor || 'Unknown vendor'}</span></td>
      <td className="mono">{row.installed_version}</td>
      <td className="score-cell">{row.cvss_score == null ? '—' : Number(row.cvss_score).toFixed(1)}</td>
      <td>{row.original_severity || '—'}</td>
      <td><span className={`match-state ${row.matched ? 'is-matched' : 'is-clear'}`}>{row.matched ? 'Affected' : 'Not affected'}</span></td>
      <td><RiskBadge level={row.risk_level} /></td>
    </tr>)}</tbody>
  </table></div>
}

function ExposureGauge({ score, assessed }) {
  const value = Math.max(0, Math.min(100, score))
  const circumference = 2 * Math.PI * 48
  return <div className="exposure-gauge" aria-label={assessed ? `Peak observed CVSS normalized to ${value} out of 100` : 'Exposure score unavailable'}>
    <svg viewBox="0 0 120 120" role="img"><circle className="gauge-track" cx="60" cy="60" r="48" /><circle className="gauge-value" cx="60" cy="60" r="48" strokeDasharray={circumference} strokeDashoffset={circumference - (circumference * value) / 100} /></svg>
    <div className="gauge-label"><strong>{assessed ? value : '—'}</strong><span>/ 100</span></div>
  </div>
}

function RiskDistribution({ rows, loading }) {
  const matched = rows.filter((row) => row.matched)
  const levels = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'UNKNOWN', 'NONE']
  const counts = levels.map((level) => [level, matched.filter((row) => String(row.risk_level).toUpperCase() === level).length])
  const denominator = Math.max(1, matched.length)
  return <section className="panel risk-distribution"><div className="panel-heading"><div><span className="eyebrow">RISK DISTRIBUTION</span><h2>Matched findings by severity</h2></div><span className="subtle-count">{loading ? 'Assessing…' : `${matched.length} matched`}</span></div>{loading ? <div className="risk-distribution-loading" aria-label="Loading severity distribution">{levels.slice(0, 4).map((level) => <div className="risk-skeleton-row" key={level}><i /><span /><b /></div>)}</div> : matched.length ? <><div className="severity-segments" role="img" aria-label={counts.filter(([, count]) => count > 0).map(([level, count]) => `${level}: ${count}`).join(', ')}>{counts.map(([level, count]) => count > 0 && <i key={level} className={`severity-segment severity-${level.toLowerCase()}`} style={{ width: `${count / denominator * 100}%` }} />)}</div><div className="risk-distribution-rows">{counts.map(([level, count]) => <div className={`risk-distribution-row severity-${level.toLowerCase()}`} key={level}><span className="risk-level-label"><i />{level === 'UNKNOWN' ? 'UNSCORED' : level}</span><div className="risk-distribution-track"><i style={{ width: `${count ? Math.max(2, count / denominator * 100) : 0}%` }} /></div><b><AnimatedValue value={count} /></b><small>{matched.length ? `${Math.round(count / matched.length * 100)}%` : '0%'}</small></div>)}</div></> : <div className="risk-distribution-empty"><span className="empty-icon"><Icon name="shield" size={19} /></span><div><strong>No matched findings in loaded assessments</strong><small>The distribution will reflect stored CVEs that match monitored software.</small></div></div>}</section>
}

function ExposureTrend({ rows }) {
  const matched = rows.filter((row) => row.matched)
  const peak = matched.reduce((max, row) => Math.max(max, Number(row.cvss_score) || 0), 0)
  const y = 148 - (peak / 10) * 112
  return <section className="panel trend-panel">
    <div className="panel-heading"><div><span className="eyebrow">EXPOSURE TREND</span><h2>Current assessment signal</h2></div><span className="trend-current"><i /> CURRENT</span></div>
    <div className="trend-visual">
      <div className="trend-axis"><span>10</span><span>7.5</span><span>5</span><span>2.5</span><span>0</span></div>
      <svg viewBox="0 0 520 170" preserveAspectRatio="none" role="img" aria-label={matched.length ? `Current peak CVSS ${peak.toFixed(1)} out of 10. Historical data is unavailable.` : 'No matched exposure in the current assessment. Historical data is unavailable.'}>
        {[24, 52, 80, 108, 148].map((line) => <line key={line} x1="8" x2="512" y1={line} y2={line} className="trend-gridline" />)}
        <line x1="511" x2="511" y1="20" y2="150" className="trend-now-line" />
        <circle cx="511" cy={y} r="7" className={matched.length ? 'trend-point is-exposed' : 'trend-point'} />
        <circle cx="511" cy={y} r="15" className="trend-halo" />
      </svg>
      <div className="trend-value"><strong>{matched.length ? peak.toFixed(1) : '—'}</strong><span>peak CVSS / 10</span></div>
      <div className="trend-time"><span>History unavailable from current API</span><b>NOW</b></div>
    </div>
  </section>
}

function SecurityInsight({ rows }) {
  const matched = rows.filter((row) => row.matched)
  const priority = [...matched].sort((a, b) => (Number(b.cvss_score) || 0) - (Number(a.cvss_score) || 0))[0]
  const insight = !priority
    ? 'No matched vulnerabilities were returned for the loaded assessments. Continue monitoring as assets and CVE data are refreshed.'
    : `${priority.asset_hostname || 'A monitored asset'} has the highest observed finding: ${priority.cve_id} in ${priority.affected_software}${priority.fixed_version ? `, with ${priority.fixed_version} listed as a fixed version` : ''}. Prioritize review of this affected component.`
  return <section className="insight-panel">
    <div className="insight-icon"><Icon name="target" size={19} /></div>
    <div className="insight-copy"><div className="insight-heading"><span className="eyebrow">AI SECURITY INSIGHT</span><span className="insight-source">ASSESSMENT SUMMARY · LIVE DATA</span></div><p>{insight}</p><small>Derived from loaded records; no external AI service is connected.</small></div>
    {priority && <div className="insight-score"><span>TOP CVSS</span><strong>{Number(priority.cvss_score || 0).toFixed(1)}</strong></div>}
  </section>
}

function CommandHero({ allRows, navigate, assessing, hasAssessment, apiState }) {
  const matched = allRows.filter((row) => row.matched)
  const maxCvss = matched.reduce((max, row) => Math.max(max, Number(row.cvss_score) || 0), 0)
  const score = Math.round(maxCvss * 10)
  const top = [...matched].sort((a, b) => (b.cvss_score ?? 0) - (a.cvss_score ?? 0))[0]
  return <section className="command-hero">
    <div className="hero-grid" />
    <div className="hero-score"><ExposureGauge score={score} assessed={hasAssessment} /><span className="gauge-caption">PEAK OBSERVED CVSS × 10</span><span className="status-chip"><i />{assessing ? 'ASSESSING ASSETS' : hasAssessment ? 'ASSESSMENT READY' : 'AWAITING ASSETS'}</span></div>
    <div className="hero-copy"><div className="hero-identity"><span className="eyebrow hero-kicker"><i /> BREACH-X <span>/ EXPOSURE INTELLIGENCE</span></span><span className={`hero-api-status ${apiState}`}><i /> API {apiState === 'online' ? 'CONNECTED' : apiState === 'offline' ? 'UNAVAILABLE' : 'CHECKING'}</span></div><h2>See exposure. Prioritize response.</h2><p>Monitor persisted assets, installed software, and locally stored CVEs to understand which components are affected and where risk is concentrated.</p><div className="hero-observation"><span className="eyebrow">CURRENT ASSESSMENT</span><strong>{assessing ? 'Evaluating asset exposure…' : hasAssessment ? `${matched.length} matched finding${matched.length === 1 ? '' : 's'} across loaded assets` : 'Waiting for asset assessments'}</strong></div>{top && <button className="hero-alert" onClick={() => navigate(`/assets/${encodeURIComponent(top.asset_id)}`)}><Icon name="target" size={16} /><span>Priority finding <b>{top.cve_id}</b><small>{top.asset_hostname} · {top.affected_software} · CVSS {top.cvss_score == null ? 'unscored' : Number(top.cvss_score).toFixed(1)}</small></span><Icon name="arrow" size={15} /></button>}</div>
  </section>
}

function ExposureGraph({ rows, assets, navigate }) {
  const links = rows.filter((row) => row.matched).slice(0, 18)
  const assetNodes = assets.slice(0, 6).map((asset, index) => ({ id: `asset:${asset.asset_id}`, kind: 'asset', label: asset.hostname, sublabel: asset.ip_address, x: 20, y: 48 + index * 66, assetId: asset.asset_id }))
  const softwareEntries = [...new Map(links.map((row) => [`software:${row.software_id}`, row])).values()].slice(0, 8)
  const softwareNodes = softwareEntries.map((row, index) => ({ id: `software:${row.software_id}`, kind: 'software', label: row.affected_software, sublabel: row.installed_version, x: 310, y: 48 + index * 50 }))
  const cveEntries = [...new Map(links.map((row) => [`cve:${row.cve_id}`, row])).values()].slice(0, 10)
  const cveNodes = cveEntries.map((row, index) => ({ id: `cve:${row.cve_id}`, kind: 'cve', label: row.cve_id, sublabel: Number(row.cvss_score).toFixed(1), severity: row.risk_level, x: 620, y: 39 + index * 39 }))
  const nodes = [...assetNodes, ...softwareNodes, ...cveNodes]
  const edges = links.flatMap((row) => [{ id: `${row.asset_id}:${row.software_id}`, from: `asset:${row.asset_id}`, to: `software:${row.software_id}`, severity: row.risk_level }, { id: `${row.software_id}:${row.cve_id}`, from: `software:${row.software_id}`, to: `cve:${row.cve_id}`, severity: row.risk_level }])
  const nodeMap = new Map(nodes.map((node) => [node.id, node]))
  const [activeId, setActiveId] = useState(null)
  const [selectedId, setSelectedId] = useState(null)
  const focusId = selectedId || activeId
  const connected = focusId ? (() => { const result = new Set([focusId]); let changed = true; while (changed) { changed = false; edges.forEach((edge) => { if (result.has(edge.from) || result.has(edge.to)) { if (!result.has(edge.from)) { result.add(edge.from); changed = true }; if (!result.has(edge.to)) { result.add(edge.to); changed = true } } }) }; return result })() : null
  const colorFor = (level) => ({ CRITICAL: '#ff6678', HIGH: '#f2a05c', MEDIUM: '#e9c45d', LOW: '#55d2bd' }[level] || '#5f7b87')
  const pathFor = (from, to) => `M ${from.x + (from.kind === 'cve' ? 0 : 180)} ${from.y} C ${(from.x + to.x) / 2} ${from.y}, ${(from.x + to.x) / 2} ${to.y}, ${to.x} ${to.y}`
  const activate = (node) => setSelectedId((current) => current === node.id ? null : node.id)
  const selectedNode = selectedId ? nodeMap.get(selectedId) : null
  const selectedRows = selectedNode?.kind === 'asset' ? links.filter((row) => row.asset_id === selectedNode.assetId) : selectedNode?.kind === 'software' ? links.filter((row) => `software:${row.software_id}` === selectedNode.id) : selectedNode?.kind === 'cve' ? links.filter((row) => `cve:${row.cve_id}` === selectedNode.id) : []
  return <section className="panel graph-panel"><div className="panel-heading"><div><span className="eyebrow">RELATIONSHIP MAP</span><h2>Asset exposure paths</h2></div><span className="subtle-count">visible nodes · asset → software → CVE</span></div>{!assets.length ? <EmptyState title="No exposure paths yet" detail="Load an asset to build relationships from live exposure data." /> : <div className="svg-graph-wrap"><div className="graph-columns"><span>ASSETS · {assetNodes.length} visible</span><span>SOFTWARE · {softwareNodes.length} visible</span><span>VULNERABILITIES · {cveNodes.length} visible</span></div><svg className="exposure-svg" viewBox="0 0 820 450" role="group" aria-label="Asset to software to vulnerability exposure graph" onMouseLeave={() => setActiveId(null)}>{edges.map((edge, index) => { const from = nodeMap.get(edge.from); const to = nodeMap.get(edge.to); if (!from || !to) return null; const lit = !connected || connected.has(edge.from) && connected.has(edge.to); const path = pathFor(from, to); return <g key={`${edge.id}-${index}`}><path id={`graph-edge-${index}`} className={`graph-edge ${lit ? 'is-lit' : 'is-dim'}`} d={path} stroke={colorFor(edge.severity)} /><circle className={`graph-particle ${lit ? 'is-lit' : 'is-dim'}`} r="2" fill={colorFor(edge.severity)}><animateMotion dur={`${2.8 + index % 3 * .5}s`} repeatCount="indefinite" begin={`${index * .12}s`}><mpath href={`#graph-edge-${index}`} /></animateMotion></circle></g> })}{nodes.map((node, index) => { const lit = !connected || connected.has(node.id); const color = colorFor(node.severity); return <g key={node.id} className={`svg-node ${lit ? 'is-lit' : 'is-dim'} ${focusId === node.id ? 'is-selected' : ''}`} tabIndex="0" role="button" aria-label={`${node.kind} ${node.label}`} onMouseEnter={() => setActiveId(node.id)} onFocus={() => setActiveId(node.id)} onBlur={() => setActiveId(null)} onClick={() => activate(node)} onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); activate(node) } }} style={{ '--node-color': color, '--node-delay': `${index * 45}ms` }}><rect className={`node-box node-${node.kind}`} x={node.x} y={node.y - 18} width={node.kind === 'asset' ? 180 : node.kind === 'software' ? 180 : 170} height="36" rx={node.kind === 'cve' ? 18 : 7} /><circle className="node-pulse" cx={node.x + (node.kind === 'cve' ? 12 : 10)} cy={node.y} r="3" fill={color} /><text x={node.x + (node.kind === 'cve' ? 25 : 22)} y={node.y - 2}>{node.label}</text><text className="node-subtext" x={node.x + (node.kind === 'cve' ? 25 : 22)} y={node.y + 12}>{node.sublabel}</text></g> })}</svg>{selectedNode && <aside className="graph-inspector"><div><span className="eyebrow">SELECTED {selectedNode.kind}</span><h3>{selectedNode.label}</h3></div><button className="icon-button" onClick={() => setSelectedId(null)} aria-label="Clear graph selection">×</button><div className="inspector-grid"><span>Related records<b>{selectedRows.length}</b></span>{selectedRows[0]?.cvss_score != null && <span>CVSS<b>{Number(selectedRows[0].cvss_score).toFixed(1)}</b></span>}{selectedRows[0]?.installed_version && <span>Installed<b>{selectedRows[0].installed_version}</b></span>}{selectedRows[0]?.affected_range && <span>Affected range<b>{selectedRows[0].affected_range}</b></span>}</div>{selectedNode.kind === 'asset' && <button className="button button-secondary" onClick={() => navigate(`/assets/${encodeURIComponent(selectedNode.assetId)}`)}>Open asset detail <Icon name="arrow" size={14} /></button>}</aside>}<div className="graph-legend"><span><i className="legend-dot critical" /> Critical</span><span><i className="legend-dot high" /> High</span><span><i className="legend-dot medium" /> Medium</span><span><i className="legend-dot low" /> Low</span><span className="graph-hint">Hover to trace · click to isolate</span></div></div>}</section>
}

function CvssRing({ score, severity }) {
  const radius = 19
  const circumference = 2 * Math.PI * radius
  const hasScore = score !== null && score !== undefined && score !== '' && Number.isFinite(Number(score))
  const value = hasScore ? Math.max(0, Math.min(10, Number(score))) : 0
  return <div className={`cvss-ring ring-${String(severity).toLowerCase()}`} aria-label={hasScore ? `CVSS ${value.toFixed(1)} out of 10` : 'CVSS score unavailable'}><svg viewBox="0 0 48 48"><circle className="cvss-track" cx="24" cy="24" r={radius} />{hasScore && <circle className="cvss-progress" cx="24" cy="24" r={radius} strokeDasharray={circumference} strokeDashoffset={circumference - circumference * value / 10} />}</svg><strong>{hasScore ? value.toFixed(1) : '—'}</strong></div>
}

function FindingCard({ row, onOpenExplorer }) {
  const severity = String(row.risk_level || row.original_severity || 'UNKNOWN').toUpperCase()
  const affectedRange = row.affected_range || [row.min_version, row.max_version].filter(Boolean).join(' – ')
  const hasDetails = row.description || affectedRange || row.fixed_version || row.affected_products?.length
  return <article className={`finding-card risk-${severity.toLowerCase()}`}><div className="finding-accent" /><header><div><RiskBadge level={severity} /><h3>{row.cve_id}</h3></div><CvssRing score={row.cvss_score} severity={severity} /></header><p className="finding-software">{row.affected_software}<span>{row.vendor || 'Unknown vendor'} · installed {row.installed_version}</span></p>{row.asset_hostname && <div className="finding-asset"><Icon name="server" size={13} /><span>{row.matched ? 'AFFECTED ASSET' : 'ASSESSED ASSET'}</span><strong>{row.asset_hostname}</strong></div>}<div className="finding-meta"><span>ASSESSMENT</span><b className={row.matched ? 'is-matched' : 'is-clear'}>{row.matched ? 'AFFECTED' : 'NOT AFFECTED'}</b></div><div className="finding-bar"><i style={{ width: `${Math.max(3, Math.min(100, Number(row.cvss_score || 0) * 10))}%` }} /></div>{hasDetails && <details className="finding-details"><summary>Assessment details</summary>{row.description && <p className="finding-description">{row.description}</p>}{(affectedRange || row.fixed_version) && <div className="finding-range">{affectedRange && <span>Affected range <b>{affectedRange}</b></span>}{row.fixed_version && <span>Fixed in <b>{row.fixed_version}</b></span>}</div>}{row.affected_products?.length > 0 && <div className="finding-products"><span>AFFECTED PRODUCT MATCHES</span>{row.affected_products.map((product, index) => <p key={`${product.vendor}-${product.product}-${index}`}>{product.vendor} / {product.product}{product.edition ? ` / ${product.edition}` : ''}<small>{product.min_version || 'Any version'}{product.max_version ? ` – ${product.max_version}` : ' and later'}</small></p>)}</div>}</details>}{onOpenExplorer && <button className="finding-explorer-link" onClick={onOpenExplorer}>Open vulnerability explorer <Icon name="arrow" size={13} /></button>}</article>
}

function AssetExposureCard({ asset, exposure, error, assessing, onOpen }) {
  const findings = exposure?.exposures.filter((row) => row.matched) || []
  const levels = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'UNKNOWN', 'NONE']
  const severityCounts = levels.map((level) => [level, findings.filter((row) => String(row.risk_level).toUpperCase() === level).length]).filter(([, count]) => count > 0)
  const softwareNames = [...new Set(findings.map((row) => row.affected_software).filter(Boolean))]
  const state = error ? 'UNAVAILABLE' : assessing && !exposure ? 'ASSESSING' : exposure ? findings.length ? 'EXPOSED' : 'NO MATCHES' : 'NOT ASSESSED'
  return <button className={`asset-exposure-card ${findings.length ? 'has-exposure' : ''}`} onClick={onOpen}>
    <div className="asset-exposure-top"><span className="asset-avatar"><Icon name="server" /></span><span className={`asset-state ${findings.length ? 'state-exposed' : state === 'NO MATCHES' ? 'state-clear' : 'state-pending'}`}><i />{state}</span></div>
    <h3>{asset.hostname || asset.asset_id}</h3><p className="asset-exposure-address">{[asset.ip_address, asset.asset_type, asset.operating_system].filter(Boolean).join(' · ') || 'Asset metadata unavailable'}</p>
    <div className="asset-exposure-count"><strong>{exposure ? findings.length : '—'}</strong><span>matched findings</span></div>
    {severityCounts.length ? <div className="asset-severity-tags">{severityCounts.map(([level, count]) => <span key={level} className={`severity-${level.toLowerCase()}`}><i />{level === 'UNKNOWN' ? 'UNSCORED' : level === 'NONE' ? 'NO SEVERITY' : level}<b>{count}</b></span>)}</div> : <div className="asset-severity-tags empty-severity"><span>{exposure ? 'No matched severity' : error ? 'Exposure request failed' : 'Assessment pending'}</span></div>}
    <div className="asset-affected-software"><span className="eyebrow">AFFECTED SOFTWARE</span><strong>{softwareNames.length ? softwareNames.slice(0, 2).join(' · ') : exposure ? 'No affected software' : 'Not yet assessed'}</strong>{softwareNames.length > 2 && <small>+{softwareNames.length - 2} more components</small>}</div>
    <span className="asset-exposure-open">Open asset profile <Icon name="arrow" size={14} /></span>
  </button>
}

function PriorityFinding({ row, onOpen }) {
  const severity = String(row.risk_level || row.original_severity || 'UNKNOWN').toUpperCase()
  return <button className="priority-finding" onClick={onOpen}>
    <span className={`priority-severity severity-${severity.toLowerCase()}`}><i />{severity}</span>
    <span className="priority-finding-main"><strong>{row.cve_id}</strong><span>{row.asset_hostname} · {row.affected_software}</span><small>{row.description || 'No description is available in the stored vulnerability record.'}</small></span>
    <span className="priority-cvss"><strong>{row.cvss_score == null ? '—' : Number(row.cvss_score).toFixed(1)}</strong><small>CVSS</small></span>
    <Icon name="arrow" size={15} />
  </button>
}

function DataUnavailable({ title, detail }) { return <section className="panel unavailable"><div className="empty-icon"><Icon name="activity" /></div><h3>{title}</h3><p>{detail}</p><span className="data-flag">LIVE API SURFACE NOT AVAILABLE</span></section> }

function Sidebar({ page, navigate, apiState, assetCount }) {
  const links = [
    { id: 'overview', label: 'Overview', path: '/', icon: 'grid' },
    { id: 'assets', label: 'Assets', path: '/assets', icon: 'server' },
    { id: 'exposures', label: 'Exposure findings', path: '/exposures', icon: 'shield' },
    { id: 'vulnerabilities', label: 'Vulnerabilities', path: '/vulnerabilities', icon: 'alert' },
    { id: 'threat-intel', label: 'Threat intelligence', path: '/threat-intel', icon: 'globe' },
    { id: 'analytics', label: 'Analytics', path: '/analytics', icon: 'trend' },
  ]
  return <motion.aside className="sidebar" initial={{ x: -10, opacity: 0 }} animate={{ x: 0, opacity: 1 }} transition={{ duration: 0.32, ease: 'easeOut' }}>
    <button className="brand" onClick={() => navigate('/')} aria-label="BREACH-X overview">
      <span className="brand-mark"><span /><span /><span /></span>
      <span className="brand-name">BREACH<span>-X</span><small>EXPOSURE CONSOLE</small></span>
    </button>
    <div className="nav-label">WORKSPACE</div>
    <nav>{links.map((link) => <motion.button key={link.id} aria-label={link.label} title={link.label} onClick={() => navigate(link.path)} className={`nav-link ${page === link.id ? 'active' : ''}`} whileHover={{ x: 2 }} whileTap={{ scale: 0.985 }}><Icon name={link.icon} /><span>{link.label}</span>{link.id === 'assets' && assetCount > 0 && <span className="nav-count">{assetCount}</span>}</motion.button>)}</nav>
    <div className="sidebar-bottom"><div className="connection"><span className={`connection-dot ${apiState}`} /><span><strong>API {apiState === 'online' ? 'reachable' : apiState === 'offline' ? 'unavailable' : 'checking'}</strong><small>FastAPI service</small></span></div><span className="sidebar-version">BREACH-X · v0.1.0</span></div>
  </motion.aside>
}

function Topbar({ title, subtitle, onLookup, loading, error }) {
  return <header className="topbar">
    <div><div className="breadcrumb">BREACH-X <span>/</span> {title}</div><h1>{title}</h1><p>{subtitle}</p></div>
    {onLookup && <AssetLookup onLookup={onLookup} loading={loading} error={error} compact />}
  </header>
}

function Overview({ assetRecords, exposureById, allRows, errorsById, onLookup, loading, error, navigate, apiState, inventoryLoading, inventoryError, onReloadAssets, assessingInventory }) {
  const softwareCount = assetRecords.reduce((total, asset) => total + (exposureById[asset.asset_id]?.software.length || 0), 0)
  const matchedRows = allRows.filter((row) => row.matched)
  const exposedAssetCount = new Set(matchedRows.map((row) => row.asset_id)).size
  const failedExposureCount = assetRecords.filter((asset) => errorsById[asset.asset_id]).length
  const priorityRows = [...matchedRows].sort((a, b) => (Number(b.cvss_score) || 0) - (Number(a.cvss_score) || 0)).slice(0, 6)
  const assetEntries = assetRecords.map((asset) => [asset.asset_id, asset])
  return <>
    <Topbar title="Overview" subtitle="Exposure intelligence across your monitored assets" onLookup={onLookup} loading={loading} error={error} />
    <section className="page-content">
      <CommandHero allRows={allRows} navigate={navigate} assessing={assessingInventory} hasAssessment={assetRecords.some((asset) => exposureById[asset.asset_id])} apiState={apiState} />
      <div className="scope-notice"><span className="notice-mark">i</span><span><strong>Inventory from API</strong> — total assets reflects <code>GET /assets</code>. {assessingInventory ? 'Assessing persisted assets…' : 'Exposure metrics reflect loaded asset assessments.'}</span></div>
      <div className="metric-grid">
        <MetricCard label="Total assets" value={inventoryLoading ? '…' : inventoryError ? '—' : assetEntries.length} note="Persisted asset inventory" icon="server" />
        <MetricCard label="Exposed assets" value={assessingInventory ? '…' : exposedAssetCount} note="Assets with matched CVEs" icon="shield" tone="red" />
        <MetricCard label="Evaluated software" value={assessingInventory ? '…' : softwareCount} note="Components from loaded assessments" icon="software" tone="blue" />
        <MetricCard label="Matched findings" value={assessingInventory ? '…' : matchedRows.length} note="Persisted CVEs affecting assets" icon="activity" tone="violet" />
      </div>
      <RiskDistribution rows={allRows} loading={assessingInventory} />
      <div className="insight-grid"><ExposureTrend rows={allRows} /><SecurityInsight rows={allRows} /></div>
      {inventoryError && <div className="inventory-error" role="alert"><Icon name="alert" size={17} /><span><strong>Asset inventory unavailable</strong><small>{inventoryError}</small></span><button className="button button-secondary" onClick={onReloadAssets}>Retry</button></div>}
      {failedExposureCount > 0 && !assessingInventory && <div className="inventory-error" role="alert"><Icon name="alert" size={17} /><span><strong>Exposure assessment incomplete</strong><small>{failedExposureCount} asset exposure request{failedExposureCount === 1 ? ' could not' : 's could not'} be loaded. Refresh the inventory to retry.</small></span><button className="button button-secondary" onClick={onReloadAssets}>Retry</button></div>}
      {inventoryLoading && assetEntries.length === 0 && <section className="panel"><LoadingState label="Loading persisted assets…" /></section>}
      {!inventoryLoading && !inventoryError && assetEntries.length === 0 && <section className="panel welcome-panel">
        <EmptyState title="No assets registered" detail="Assets persisted through the BREACH-X API will appear here." action={<button className="button button-secondary" onClick={onReloadAssets}>Refresh inventory</button>} />
      </section>}
      {assetEntries.length > 0 && <section className="panel asset-overview-panel"><div className="panel-heading"><div><span className="eyebrow">EXPOSURE OVERVIEW</span><h2>Assets requiring attention</h2></div><button className="text-button" onClick={() => navigate('/assets')}>Explore all assets <Icon name="arrow" size={15} /></button></div><div className="asset-exposure-grid">{assetEntries.map(([id, asset]) => <AssetExposureCard key={id} asset={asset} exposure={exposureById[id]} error={errorsById[id]} assessing={assessingInventory} onOpen={() => navigate(`/assets/${encodeURIComponent(id)}`)} />)}</div></section>}
      <section className="panel overview-priority-panel"><div className="panel-heading"><div><span className="eyebrow">PRIORITY FINDINGS</span><h2>Highest observed risk</h2></div><button className="text-button" onClick={() => navigate('/vulnerabilities')}>View vulnerability explorer <Icon name="arrow" size={15} /></button></div>{priorityRows.length ? <div className="priority-finding-list">{priorityRows.map((row, index) => <PriorityFinding key={`${row.asset_id}-${row.cve_id}-${row.software_id}-${index}`} row={row} onOpen={() => navigate(`/assets/${encodeURIComponent(row.asset_id)}`)} />)}</div> : <EmptyState title="No matched findings" detail="No stored CVEs matched the software returned by the loaded asset assessments." />}</section>
      <ExposureGraph rows={allRows} assets={assetRecords} navigate={navigate} />
      <footer className="page-foot"><Icon name="clock" size={14} /> Assessment data is retrieved live from the BREACH-X API. Exposure checks cover vulnerabilities currently stored locally.</footer>
    </section>
  </>
}

function AssetsPage({ assetRecords, exposureById, errorsById, onLookup, loading, error, navigate, inventoryLoading, inventoryError, onReloadAssets, assessingInventory }) {
  // #region agent log
  fetch('http://127.0.0.1:7723/ingest/73e337ca-b123-45e1-8b5c-2dd62a3fdfad',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'b40d23'},body:JSON.stringify({sessionId:'b40d23',runId:'pre-fix',hypothesisId:'A',location:'App.jsx:AssetsPage',message:'AssetsPage received props',data:{hasErrorsById:errorsById!=null,errorsByIdType:typeof errorsById,hasAssessingInventory:typeof assessingInventory!=='undefined',hasAssetRecords:Array.isArray(assetRecords),assetCount:Array.isArray(assetRecords)?assetRecords.length:-1,hasAssetsProp:false,hasOnLoadAsset:false,hasSelectedAssetId:false},timestamp:Date.now()})}).catch(()=>{});
  // #endregion
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState('all')
  const entries = assetRecords
  const exposedCount = entries.filter((asset) => exposureById[asset.asset_id]?.exposures.some((row) => row.matched)).length
  const noMatchCount = entries.filter((asset) => exposureById[asset.asset_id] && !exposureById[asset.asset_id].exposures.some((row) => row.matched)).length
  const filteredEntries = useMemo(() => entries.filter((asset) => {
    const data = exposureById[asset.asset_id]
    const hasMatches = data?.exposures.some((row) => row.matched) || false
    const matchesFilter = filter === 'all' || (filter === 'exposed' && hasMatches) || (filter === 'clear' && Boolean(data) && !hasMatches)
    const query = search.trim().toLowerCase()
    const matchesSearch = !query || [asset.asset_id, asset.hostname, asset.ip_address].some((value) => String(value || '').toLowerCase().includes(query))
    return matchesFilter && matchesSearch
  }), [entries, exposureById, filter, search])
  const filters = [
    { id: 'all', label: 'All', count: entries.length },
    { id: 'exposed', label: 'Exposed', count: exposedCount },
    { id: 'clear', label: 'No Matches', count: noMatchCount },
  ]
  return <>
    <Topbar title="Asset Intelligence" subtitle="Monitored assets, installed software, and exposure findings" onLookup={onLookup} loading={loading} error={error} />
    <section className="page-content">
      <section className="panel inventory-panel asset-intelligence-panel">
        <div className="panel-heading"><div><span className="eyebrow">PERSISTED INVENTORY</span><h2>Asset inventory</h2><p className="inventory-description">BREACH-X maps monitored assets to installed software and the CVEs assessed against them.</p></div><button className="button button-secondary" onClick={onReloadAssets} disabled={inventoryLoading}>{inventoryLoading ? 'Refreshing…' : 'Refresh inventory'}</button></div>
        {inventoryError && <div className="inventory-error compact-error" role="alert"><Icon name="alert" size={17} /><span><strong>Unable to load assets</strong><small>{inventoryError}</small></span></div>}
        <div className="asset-inventory-controls"><label className="asset-search"><Icon name="search" size={17} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search asset ID, name, or IP" aria-label="Search assets by ID, name, or IP address" />{search && <button type="button" onClick={() => setSearch('')} aria-label="Clear asset search">×</button>}</label><div className="asset-filter-pills" role="group" aria-label="Filter assets">{filters.map((item) => <button key={item.id} aria-pressed={filter === item.id} className={filter === item.id ? 'selected' : ''} onClick={() => setFilter(item.id)}>{item.label}<span>{item.count}</span></button>)}</div><span className="asset-result-count" role="status">{filteredEntries.length} of {entries.length} assets</span></div>
        {inventoryLoading && entries.length === 0 ? <div className="asset-inventory-skeleton" aria-label="Loading asset inventory">{[0, 1, 2].map((index) => <div key={index}><i /><span /><b /><small /></div>)}</div> : filteredEntries.length ? <motion.div layout className="asset-intelligence-grid"><AnimatePresence initial={false} mode="popLayout">{filteredEntries.map((asset) => {
          // #region agent log
          fetch('http://127.0.0.1:7723/ingest/73e337ca-b123-45e1-8b5c-2dd62a3fdfad',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'b40d23'},body:JSON.stringify({sessionId:'b40d23',runId:'pre-fix',hypothesisId:'C',location:'App.jsx:AssetsPage:card',message:'indexing errorsById for asset card',data:{assetId:asset.asset_id,canIndexErrorsById:errorsById!=null,errorValue:errorsById!=null?String(Boolean(errorsById[asset.asset_id])):'CRASH_IF_INDEX'},timestamp:Date.now()})}).catch(()=>{});
          // #endregion
          return <motion.div layout key={asset.asset_id} className="asset-intelligence-card-wrap" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -5 }} transition={{ duration: 0.2 }}><AssetExposureCard asset={asset} exposure={exposureById[asset.asset_id]} error={errorsById[asset.asset_id]} assessing={assessingInventory} onOpen={() => navigate(`/assets/${encodeURIComponent(asset.asset_id)}`)} /></motion.div>
        })}</AnimatePresence></motion.div> : inventoryError && entries.length === 0 ? null : entries.length ? <EmptyState title="No assets match this view" detail="Try a different search or return to the full inventory." action={<button className="button button-secondary" onClick={() => { setSearch(''); setFilter('all') }}>Clear search and filters</button>} /> : <EmptyState title="No assets registered" detail="Assets persisted through the BREACH-X API will appear here." />}
      </section>
    </section>
  </>
}

function AssetDetail({ assetId, result, loading, error, onRetry, navigate }) {
  if (loading && !result) return <><Topbar title="Asset detail" subtitle={`Loading ${assetId}`} /><section className="page-content"><section className="panel"><LoadingState /></section></section></>
  if (error && !result) return <><Topbar title="Asset detail" subtitle={`Asset ${assetId}`} /><section className="page-content"><section className="panel"><EmptyState title="Could not load this asset" detail={error} action={<button className="button button-primary" onClick={onRetry}>Try again</button>} /></section></section></>
  if (!result) return null
  const { asset, software, exposures } = result
  const matched = exposures.filter((row) => row.matched)
  const peakCvss = matched.reduce((max, row) => Math.max(max, Number(row.cvss_score) || 0), 0)
  const severityCounts = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map((level) => [level, matched.filter((row) => String(row.risk_level).toUpperCase() === level).length])
  const remediation = [...matched].sort((a, b) => (Number(b.cvss_score) || 0) - (Number(a.cvss_score) || 0)).slice(0, 3)
  return <>
    <Topbar title="Asset detail" subtitle="Installed software and vulnerability exposure" />
    <section className="page-content">
      <button className="back-link" onClick={() => navigate('/assets')}><Icon name="back" size={16} /> Back to assets</button>
      <section className="panel asset-hero"><div className="asset-hero-icon"><Icon name="server" size={23} /></div><div className="asset-hero-info"><span className="eyebrow">{asset.asset_type} · {asset.criticality} criticality</span><h2>{asset.hostname}</h2><p>{asset.ip_address} <span>·</span> {asset.operating_system || 'Operating system not specified'}</p><code>ASSET ID · {asset.asset_id}</code></div><div className="asset-hero-stats"><div><strong>{software.length}</strong><span>Software</span></div><div><strong>{matched.length}</strong><span>Affected findings</span></div></div></section>
      <div className="asset-profile-grid">
        <section className="panel asset-risk-panel"><div className="panel-heading"><div><span className="eyebrow">EXPOSURE PROFILE</span><h2>Observed risk</h2></div><span className={`asset-state ${matched.length ? 'state-exposed' : 'state-clear'}`}><i />{matched.length ? 'EXPOSED' : 'NO MATCHES'}</span></div><div className="asset-risk-body"><ExposureGauge score={Math.round(peakCvss * 10)} assessed={exposures.length > 0} /><div><strong>{matched.length ? `${peakCvss.toFixed(1)} / 10 peak CVSS` : 'No matched CVEs'}</strong><p>{matched.length ? `${matched.length} matched finding${matched.length === 1 ? '' : 's'} across ${new Set(matched.map((row) => row.software_id)).size} software component${new Set(matched.map((row) => row.software_id)).size === 1 ? '' : 's'}.` : 'The current assessment returned no matching stored CVEs for this asset.'}</p><small>Score reflects the highest observed CVSS, not a historical trend.</small></div></div></section>
        <section className="panel asset-severity-panel"><div className="panel-heading"><div><span className="eyebrow">SEVERITY DISTRIBUTION</span><h2>Matched findings</h2></div><span className="subtle-count">{matched.length} total</span></div><div className="asset-severity-list">{severityCounts.map(([level, count]) => <div className={`asset-severity-row severity-${level.toLowerCase()}`} key={level}><span><i />{level}</span><div><i style={{ width: `${matched.length ? Math.max(count ? 4 : 0, count / matched.length * 100) : 0}%` }} /></div><b>{count}</b></div>)}</div></section>
      </div>
      <div className="asset-remediation-grid">
        <section className="panel remediation-panel"><div className="panel-heading"><div><span className="eyebrow">REMEDIATION FOCUS</span><h2>Priority components</h2></div></div>{remediation.length ? <div className="remediation-list">{remediation.map((row) => <div className="remediation-item" key={`${row.cve_id}-${row.software_id}`}><RiskBadge level={row.risk_level} /><div><strong>{row.affected_software}</strong><small>{row.cve_id} · CVSS {Number(row.cvss_score || 0).toFixed(1)}</small></div><span className="remediation-action">{row.fixed_version ? `FIX: ${row.fixed_version}` : 'REVIEW VENDOR GUIDANCE'}</span></div>)}</div> : <p className="remediation-empty">No remediation items were identified in the current assessment.</p>}</section>
        <section className="panel timeline-panel"><div className="panel-heading"><div><span className="eyebrow">ASSESSMENT TIMELINE</span><h2>Current snapshot</h2></div></div><div className="timeline-current"><i /><div><strong>Latest available assessment</strong><small>{exposures.length} exposure records returned for this asset</small></div><span>CURRENT</span></div><p>Historical snapshots are not provided by the current API.</p></section>
      </div>
      <section className="panel detail-software"><div className="panel-heading"><div><span className="eyebrow">INVENTORY</span><h2>Installed software</h2></div><span className="subtle-count">{software.length} entries</span></div>
        {software.length ? <div className="table-scroll"><table className="data-table"><thead><tr><th>Software</th><th>Vendor</th><th>Installed version</th><th>Assessment</th></tr></thead><tbody>{software.map((item) => { const findings = exposures.filter((row) => row.software_id === item.software_id); const affectedCount = findings.filter((row) => row.matched).length; return <tr key={item.software_id}><td className="software-cell"><strong>{item.name}</strong><span>{item.software_id}</span></td><td>{item.vendor}</td><td className="mono">{item.version}</td><td>{affectedCount ? <span className="match-state is-matched">{affectedCount} affected</span> : <span className="match-state is-clear">No affected CVEs</span>}</td></tr> })}</tbody></table></div> : <EmptyState title="No software registered" detail="No installed software is associated with this asset yet." />}
      </section>
      <section className="panel"><div className="panel-heading"><div><span className="eyebrow">VULNERABILITY ASSESSMENT</span><h2>Matched vulnerabilities</h2></div><span className="subtle-count">{matched.length} findings</span></div><ExposureTable rows={matched} emptyTitle="No vulnerabilities affect this asset" /></section>
    </section>
  </>
}

function ExposuresPage({ rows, assets, assetRecords, onLookup, loading, error, navigate }) {
  const [filter, setFilter] = useState('all')
  const filtered = filter === 'affected' ? rows.filter((row) => row.matched) : rows
  const withAsset = filtered.map((row) => {
    const result = assets[row.asset_id]
    return { ...row, asset_hostname: result?.asset.hostname }
  })
  return <>
    <Topbar title="Exposure findings" subtitle="Vulnerability checks across loaded assets" onLookup={onLookup} loading={loading} error={error} />
    <section className="page-content"><div className="scope-notice"><span className="notice-mark">i</span><span>Assessments cover locally stored CVEs and assets whose exposure details have been fetched. The backend does not expose a global exposure feed.</span></div><ExposureGraph rows={rows} assets={assetRecords} navigate={navigate} />
      <section className="panel"><div className="panel-heading exposure-heading"><div><span className="eyebrow">EXPOSURE ASSESSMENTS</span><h2>Software-to-CVE results</h2></div><div className="exposure-heading-tools"><span className="subtle-count">{withAsset.length} evaluated</span><div className="filter-pills" aria-label="Filter exposure assessments"><button aria-pressed={filter === 'all'} className={filter === 'all' ? 'selected' : ''} onClick={() => setFilter('all')}>All evaluated</button><button aria-pressed={filter === 'affected'} className={filter === 'affected' ? 'selected' : ''} onClick={() => setFilter('affected')}>Affected only</button></div></div></div><ExposureTable rows={withAsset} showAsset emptyTitle={filter === 'affected' ? 'No affected vulnerabilities' : 'No exposure checks yet'} /></section>
      {!rows.length && <section className="panel lookup-panel"><p className="muted-copy">Load an asset to retrieve its exposure data.</p><AssetLookup onLookup={onLookup} loading={loading} error={error} /></section>}
    </section>
  </>
}

function VulnerabilitiesPage({ rows, onLookup, loading, error }) {
  const [filter, setFilter] = useState('all')
  const affected = rows.filter((row) => row.matched)
  const filtered = filter === 'affected' ? affected : rows
  return <><Topbar title="Vulnerabilities" subtitle="CVE intelligence from live asset assessments" onLookup={onLookup} loading={loading} error={error} /><section className="page-content"><div className="intel-strip"><span><Icon name="shield" size={16} />{new Set(affected.map((row) => row.cve_id)).size} unique CVEs observed</span><span><Icon name="target" size={16} />{affected.length} affected relationships</span><div className="filter-pills"><button className={filter === 'all' ? 'selected' : ''} onClick={() => setFilter('all')}>All evaluated</button><button className={filter === 'affected' ? 'selected' : ''} onClick={() => setFilter('affected')}>Affected only</button></div></div>{filtered.length ? <div className="finding-grid">{filtered.map((row, index) => <FindingCard key={`${row.cve_id}-${row.software_id}-${index}`} row={row} />)}</div> : <section className="panel"><EmptyState title="No vulnerability intelligence loaded" detail="Load an asset to retrieve live CVE assessments from the existing API." /></section>}{!rows.length && <DataUnavailable title="Assessment data is not loaded" detail="Use the asset lookup or open an asset to retrieve live CVE assessments from the existing API." />}</section></>
}

function ThreatIntelPage() {
  return <><Topbar title="Threat intelligence" subtitle="External intelligence signals and analyst context" /><section className="page-content"><DataUnavailable title="Threat feed not exposed by the current API" detail="BREACH-X is keeping this surface ready for integration. No mock events or invented threat signals are shown." /><div className="content-grid"><section className="panel intel-placeholder"><span className="eyebrow">SIGNAL PIPELINE</span><h2>Event ingestion</h2><p>Connect a backend threat-event endpoint here when it becomes available. The current production API remains unchanged.</p><div className="pipeline"><span>API</span><i /><span>EVENTS</span><i /><span>ANALYST VIEW</span></div></section><section className="panel intel-placeholder"><span className="eyebrow">CONTEXT WINDOW</span><h2>What is being assessed?</h2><p>Loaded software and locally stored CVEs are the only intelligence currently available to this console.</p><div className="context-list"><span><Icon name="server" size={15} />Asset inventory</span><span><Icon name="software" size={15} />Installed software</span><span><Icon name="alert" size={15} />CVE matches</span></div></section></div></section></>
}

function AnalyticsPage({ rows, assets, assessedCount }) {
  const matched = rows.filter((row) => row.matched)
  const severity = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']
  const max = Math.max(1, ...severity.map((level) => matched.filter((row) => row.risk_level === level).length))
  return <><Topbar title="Analytics" subtitle="Derived posture metrics from inventory-scoped assessments" /><section className="page-content"><section className="panel analytics-hero"><div><span className="eyebrow">LIVE ASSESSMENT SNAPSHOT</span><h2>{matched.length ? 'Exposure is measurable across the monitored estate.' : 'Load asset exposure to begin analysis.'}</h2><p>Severity counts use matched rows from assets returned by GET /assets. No historical data is invented.</p></div><div className="analytics-total"><strong>{matched.length}</strong><span>matched findings</span></div></section><div className="analytics-grid"><section className="panel chart-panel"><div className="panel-heading"><div><span className="eyebrow">SEVERITY DISTRIBUTION</span><h2>Risk levels</h2></div></div><div className="bar-chart">{severity.map((level) => { const count = matched.filter((row) => row.risk_level === level).length; return <div className="bar-row" key={level}><span>{level}</span><div><i className={`bar-fill bar-${level.toLowerCase()}`} style={{ width: `${(count / max) * 100}%` }} /></div><b>{count}</b></div> })}</div></section><section className="panel chart-panel"><div className="panel-heading"><div><span className="eyebrow">INVENTORY COVERAGE</span><h2>Exposure data loaded</h2></div></div><div className="coverage-ring"><ExposureGauge score={assets.length ? Math.round((assessedCount / Math.max(1, assets.length)) * 100) : 0} assessed={assessedCount > 0} /><div><strong>{assessedCount} / {assets.length}</strong><span>monitored assets assessed</span><small>Coverage is based on successful exposure responses.</small></div></div></section></div></section></>
}

export default function App() {
  const [pathname, setPathname] = useState(window.location.pathname)
  const [assetRecords, setAssetRecords] = useState([])
  const [exposureById, setExposureById] = useState({})
  const [inventoryLoading, setInventoryLoading] = useState(true)
  const [inventoryError, setInventoryError] = useState('')
  const [loadingIds, setLoadingIds] = useState([])
  const [errors, setErrors] = useState({})
  const [lookupError, setLookupError] = useState('')
  const [apiState, setApiState] = useState('checking')
  const [assessingInventory, setAssessingInventory] = useState(false)

  const navigate = useCallback((path) => {
    window.history.pushState({}, '', path)
    setPathname(path)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }, [])

  useEffect(() => {
    const onPopState = () => setPathname(window.location.pathname)
    window.addEventListener('popstate', onPopState)
    return () => window.removeEventListener('popstate', onPopState)
  }, [])

  useEffect(() => {
    let active = true
    checkApi().then(() => {
      if (active) setApiState('online')
    }).catch(() => {
      if (active) setApiState('offline')
    })
    return () => { active = false }
  }, [])

  const refreshAssets = useCallback(async () => {
    setInventoryLoading(true)
    setInventoryError('')
    try {
      const records = await getAssets()
      setAssetRecords(records)
      if (!records.length) setAssessingInventory(false)
    } catch (error) {
      setInventoryError(error.message)
      setAssessingInventory(false)
    } finally {
      setInventoryLoading(false)
    }
  }, [])

  useEffect(() => {
    void refreshAssets()
  }, [refreshAssets])

  useEffect(() => {
    if (inventoryLoading || !assetRecords.length) return undefined
    let active = true
    setAssessingInventory(true)
    setErrors((current) => {
      const next = { ...current }
      assetRecords.forEach((asset) => { next[asset.asset_id] = '' })
      return next
    })
    Promise.allSettled(assetRecords.map((asset) => getAssetExposure(asset.asset_id))).then((results) => {
      if (!active) return
      setExposureById((current) => {
        const next = { ...current }
        results.forEach((result, index) => {
          if (result.status === 'fulfilled') next[assetRecords[index].asset_id] = result.value
        })
        return next
      })
      setErrors((current) => {
        const next = { ...current }
        results.forEach((result, index) => {
          const assetId = assetRecords[index].asset_id
          next[assetId] = result.status === 'rejected' ? result.reason?.message || 'Unable to load asset exposure.' : ''
        })
        return next
      })
      setAssessingInventory(false)
    })
    return () => { active = false }
  }, [assetRecords, inventoryLoading])

  const loadAsset = useCallback(async (assetId) => {
    setLookupError('')
    setErrors((current) => ({ ...current, [assetId]: '' }))
    setLoadingIds((current) => current.includes(assetId) ? current : [...current, assetId])
    try {
      const result = await getAssetExposure(assetId)
      setExposureById((current) => ({ ...current, [assetId]: result }))
      return result
    } catch (error) {
      setErrors((current) => ({ ...current, [assetId]: error.message }))
      setLookupError(error.message)
      return null
    } finally {
      setLoadingIds((current) => current.filter((id) => id !== assetId))
    }
  }, [])

  const detailMatch = pathname.match(/^\/assets\/([^/]+)$/)
  const detailAssetId = detailMatch ? decodeURIComponent(detailMatch[1]) : ''
  useEffect(() => {
    if (detailAssetId && !exposureById[detailAssetId] && !loadingIds.includes(detailAssetId)) {
      void loadAsset(detailAssetId)
    }
  }, [detailAssetId, exposureById, loadingIds, loadAsset])

  const allRows = useMemo(() => assetRecords.flatMap((asset) => {
    const result = exposureById[asset.asset_id]
    return result ? result.exposures.map((row) => ({ ...row, asset_id: asset.asset_id, asset_hostname: result.asset.hostname })) : []
  }), [assetRecords, exposureById])
  const loadingCurrent = detailAssetId ? loadingIds.includes(detailAssetId) : loadingIds.length > 0
  const page = detailAssetId ? 'assets' : pathname === '/assets' ? 'assets' : pathname === '/exposures' ? 'exposures' : pathname === '/vulnerabilities' ? 'vulnerabilities' : pathname === '/threat-intel' ? 'threat-intel' : pathname === '/analytics' ? 'analytics' : 'overview'

  async function handleLookup(assetId) {
    const result = await loadAsset(assetId)
    if (result) navigate(`/assets/${encodeURIComponent(assetId)}`)
  }

  function renderPage() {
    // #region agent log
    fetch('http://127.0.0.1:7723/ingest/73e337ca-b123-45e1-8b5c-2dd62a3fdfad',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'b40d23'},body:JSON.stringify({sessionId:'b40d23',runId:'pre-fix',hypothesisId:'B',location:'App.jsx:renderPage',message:'renderPage branch',data:{pathname,hasDetailAssetId:Boolean(detailAssetId),errorsDefined:typeof errors!=='undefined',errorsIsObject:errors!=null&&typeof errors==='object',assessingInventory,willRenderAssetsPage:pathname==='/assets'&&!detailAssetId},timestamp:Date.now()})}).catch(()=>{});
    // #endregion
    if (detailAssetId) return <AssetDetail assetId={detailAssetId} result={exposureById[detailAssetId]} loading={loadingIds.includes(detailAssetId)} error={errors[detailAssetId]} onRetry={() => loadAsset(detailAssetId)} navigate={navigate} />
    if (pathname === '/assets') return <AssetsPage assetRecords={assetRecords} exposureById={exposureById} errorsById={errors} onLookup={handleLookup} loading={loadingCurrent} error={lookupError} navigate={navigate} inventoryLoading={inventoryLoading} inventoryError={inventoryError} onReloadAssets={refreshAssets} assessingInventory={assessingInventory} />
    if (pathname === '/exposures') return <ExposuresPage rows={allRows} assets={exposureById} assetRecords={assetRecords} onLookup={handleLookup} loading={loadingCurrent} error={lookupError} navigate={navigate} />
    if (pathname === '/vulnerabilities') return <VulnerabilitiesPage rows={allRows} onLookup={handleLookup} loading={loadingCurrent} error={lookupError} />
    if (pathname === '/threat-intel') return <ThreatIntelPage />
    if (pathname === '/analytics') return <AnalyticsPage rows={allRows} assets={assetRecords} assessedCount={assetRecords.filter((asset) => exposureById[asset.asset_id]).length} />
    return <Overview assetRecords={assetRecords} exposureById={exposureById} allRows={allRows} errorsById={errors} onLookup={handleLookup} loading={loadingCurrent} error={lookupError} navigate={navigate} apiState={apiState} inventoryLoading={inventoryLoading} inventoryError={inventoryError} onReloadAssets={refreshAssets} assessingInventory={assessingInventory} />
  }

  return <MotionConfig reducedMotion="user"><div className="app-shell"><Sidebar page={page} navigate={navigate} apiState={apiState} assetCount={assetRecords.length} /><main className="main-shell"><div className="mobile-brand"><button className="brand" onClick={() => navigate('/')}><span className="brand-mark"><span /><span /><span /></span><span className="brand-name">BREACH<span>-X</span></span></button><span className={`live-indicator ${apiState}`}><i /> API {apiState === 'online' ? 'reachable' : apiState === 'offline' ? 'unavailable' : 'checking'}</span></div><AnimatePresence mode="wait" initial={false}><motion.div key={pathname} className="route-transition" initial={{ opacity: 0, y: 7 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -4 }} transition={{ duration: 0.2, ease: 'easeOut' }}>{renderPage()}</motion.div></AnimatePresence></main></div></MotionConfig>
}
