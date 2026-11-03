/* ═══════════════════════════════════════════════════════════════
   CrimeGraph AI — Main Application JavaScript
   Handles: Tab navigation, D3.js graph, Chart.js analytics,
   API calls, search, suspect cards, FIR table, CDR table,
   financial intel, communities, and modal.
   ═══════════════════════════════════════════════════════════════ */

// ─── State ────────────────────────────────────────────────────────
const State = {
  currentTab: 'dashboard',
  graphData: null,
  personsData: null,
  analyticsData: null,
  charts: {},
  d3Simulation: null,
  d3Zoom: null,
  svg: null,
  g: null,
};

// ─── Utility Functions ────────────────────────────────────────────
const API = {
  async get(endpoint) {
    try {
      const res = await fetch(endpoint);
      if (res.status === 401) { window.location = '/login'; return null; }
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (e) {
      console.error(`API Error [${endpoint}]:`, e);
      return null;
    }
  },
  // Returns { ok, status, data } so callers can show validation errors
  async post(endpoint, body) {
    const res = await fetch(endpoint, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    });
    if (res.status === 401) { window.location = '/login'; return { ok: false, status: 401, data: null }; }
    let data = null;
    try { data = await res.json(); } catch (e) { /* empty body */ }
    return { ok: res.ok, status: res.status, data };
  }
};

function fmt(n) {
  if (n === null || n === undefined) return '--';
  if (typeof n === 'number') {
    if (n >= 1e7) return (n / 1e7).toFixed(1) + 'Cr';
    if (n >= 1e5) return (n / 1e5).toFixed(1) + 'L';
    if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
    return n.toString();
  }
  return n;
}

function fmtAmount(n, currency='INR') {
  if (!n) return '—';
  const sym = { INR:'₹', USD:'$', AED:'AED', EUR:'€', BTC:'₿' };
  return `${sym[currency] || ''}${fmt(n)}`;
}

function esc(v) {
  return String(v ?? '').replace(/[&<>"']/g, c => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' }[c]));
}

function statusClass(st) {
  return 'tag-status-' + String(st || '').replace(/[^A-Za-z]/g, '');
}

function categoryBadge(cat) {
  return `<span class="cat-badge cat-${esc(cat)}">${esc(cat || '—')}</span>`;
}

function fillSelect(id, values, allLabel) {
  const el = document.getElementById(id);
  if (!el) return;
  const cur = el.value;
  el.innerHTML = (allLabel !== null ? `<option value="">${allLabel}</option>` : '') +
    values.map(v => `<option value="${esc(v)}">${esc(v)}</option>`).join('');
  if (values.includes(cur)) el.value = cur;
}

// Dropdown options (states, districts, crime hierarchy) from /api/meta
async function loadMeta() {
  if (State.meta) return State.meta;
  State.meta = await API.get('/api/meta');
  const m = State.meta;
  if (!m) return null;
  const states = Object.keys(m.states).sort();
  ['fir-state', 'an-state', 'suspect-state'].forEach(id => fillSelect(id, states, 'All States'));
  ['fir-category', 'an-category'].forEach(id => fillSelect(id, Object.keys(m.crime_hierarchy), 'All Categories'));
  fillSelect('fir-status', m.fir_statuses, 'All Status');
  fillSelect('fir-crime', allSubcategories(''), 'All Sub-categories');
  return m;
}

function allSubcategories(category) {
  const h = State.meta?.crime_hierarchy || {};
  const cats = category ? [category] : Object.keys(h);
  return cats.flatMap(c => Object.values(h[c] || {}).flat());
}

function fmtDate(d) {
  if (!d) return '—';
  return d.split('T')[0];
}

function getThreatClass(score) {
  if (score >= 0.7) return 'threat-critical';
  if (score >= 0.45) return 'threat-high';
  if (score >= 0.25) return 'threat-medium';
  return 'threat-low';
}

function getRiskClass(score) {
  if (score >= 0.5) return 'risk-high';
  if (score >= 0.3) return 'risk-medium';
  return 'risk-low';
}

function getNodeColor(node) {
  if (node.status === 'Fugitive') return '#a855f7';
  if (node.threat_score >= 0.6) return '#ef4444';
  if (node.threat_score >= 0.3) return '#f97316';
  return '#22c55e';
}

function getAvatarLetters(name) {
  return name.split(' ').slice(0, 2).map(w => w[0]).join('');
}

function animateNumber(el, target, duration=800) {
  const start = Date.now();
  const from = 0;
  const step = () => {
    const t = Math.min((Date.now() - start) / duration, 1);
    const ease = t < 0.5 ? 2*t*t : -1+(4-2*t)*t;
    el.textContent = Math.round(from + (target - from) * ease);
    if (t < 1) requestAnimationFrame(step);
    else el.textContent = target;
  };
  requestAnimationFrame(step);
}

// ─── Tab Navigation ───────────────────────────────────────────────
function switchTab(tab) {
  // Update nav
  document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
  const navEl = document.getElementById(`nav-${tab}`);
  if (navEl) navEl.classList.add('active');

  // Update tabs
  document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
  const tabEl = document.getElementById(`tab-${tab}`);
  if (tabEl) tabEl.classList.add('active');

  // Update breadcrumb
  const names = {
    dashboard: 'Dashboard', network: 'Network Graph', suspects: 'Suspects',
    firs: 'FIR Records', financial: 'Financial Intel', cdr: 'CDR Analysis',
    communities: 'Criminal Groups', analytics: 'Analytics', legal: 'Possible Lawful Action',
    addrecord: 'Add Record', investigations: 'Investigation Tracking'
  };
  document.getElementById('breadcrumb-current').textContent = names[tab] || tab;
  State.currentTab = tab;

  // Lazy-load tab data
  if (tab === 'network' && !State.graphLoaded) { loadGraph(); State.graphLoaded = true; }
  if (tab === 'suspects' && !State.suspectsLoaded) { loadSuspects(); State.suspectsLoaded = true; }
  if (tab === 'firs' && !State.firsLoaded) { loadFIRs(); State.firsLoaded = true; }
  if (tab === 'financial' && !State.financialLoaded) { loadTransactions(); State.financialLoaded = true; }
  if (tab === 'cdr' && !State.cdrLoaded) { loadCDRs(); State.cdrLoaded = true; }
  if (tab === 'communities' && !State.commLoaded) { loadCommunities(); State.commLoaded = true; }
  if (tab === 'analytics' && !State.analyticsLoaded) { loadAnalytics(); State.analyticsLoaded = true; }
  if (tab === 'legal' && !State.legalLoaded) { loadLegal(); State.legalLoaded = true; }
  if (tab === 'addrecord' && !State.recordFormReady) { initRecordForm(); State.recordFormReady = true; }
  if (tab === 'investigations') { loadInvestigations(); }
}

// Bind nav clicks
document.querySelectorAll('.nav-item').forEach(el => {
  el.addEventListener('click', e => {
    e.preventDefault();
    switchTab(el.dataset.tab);
  });
});

// Sidebar toggle
document.getElementById('sidebar-toggle').addEventListener('click', () => {
  const sidebar = document.getElementById('sidebar');
  const main = document.getElementById('main-content');
  sidebar.classList.toggle('collapsed');
  main.classList.toggle('expanded');
});

// ─── Dashboard ────────────────────────────────────────────────────
async function loadDashboard() {
  const stats = await API.get('/api/stats');
  if (!stats) return;

  document.querySelectorAll('.kpi-card').forEach(c => c.classList.remove('loading'));

  const map = {
    'kpi-high-risk': stats.high_risk_count,
    'kpi-firs': stats.total_firs,
    'kpi-nodes': stats.graph_nodes,
    'kpi-transactions': stats.total_transactions,
    'kpi-groups': stats.num_communities,
    'kpi-fugitives': stats.fugitives,
  };

  Object.entries(map).forEach(([id, val]) => {
    const el = document.getElementById(id);
    if (el) animateNumber(el, val);
  });

  document.getElementById('alert-count').textContent = stats.high_risk_count;

  // Load top suspects
  const suspects = await API.get('/api/suspects?n=8');
  renderTopSuspects(suspects || []);

  // Load recent FIRs
  const firs = await API.get('/api/firs');
  renderRecentFIRs((firs || []).slice(0, 6));

  // Load analytics for dashboard charts
  const analytics = await API.get('/api/analytics');
  State.analyticsData = analytics;
  if (analytics) {
    renderMiniChart(analytics);
    renderLocationBars(analytics.location_activity || {});
  }
  // Mini network
  loadMiniNetwork();
}

function renderTopSuspects(suspects) {
  const container = document.getElementById('top-suspects-list');
  if (!suspects.length) { container.innerHTML = '<div style="color:var(--text-muted);text-align:center;padding:20px">No data</div>'; return; }

  const colors = ['#ef4444','#f97316','#eab308','#22c55e','#3b82f6','#6366f1','#a855f7','#06b6d4'];
  container.innerHTML = suspects.map((s, i) => `
    <div class="suspect-mini-item" onclick="openPersonModal('${s.id}')">
      <div class="suspect-mini-rank">#${i+1}</div>
      <div class="suspect-mini-avatar" style="border-color:${colors[i % colors.length]};color:${colors[i % colors.length]}">
        ${getAvatarLetters(s.name)}
      </div>
      <div class="suspect-mini-info">
        <div class="suspect-mini-name">${s.name}</div>
        <div class="suspect-mini-role">${s.role || 'Unknown'} · ${s.location || '--'}</div>
      </div>
      <div class="threat-pill ${getThreatClass(s.computed_threat_score || 0)}">
        ${((s.computed_threat_score || 0) * 100).toFixed(0)}%
      </div>
    </div>
  `).join('');
}

function renderRecentFIRs(firs) {
  const container = document.getElementById('recent-firs-list');
  container.innerHTML = firs.map(f => `
    <div class="fir-mini-item" onclick="openFIRModal('${f.fir_id}')" style="cursor:pointer">
      <div class="fir-mini-header">
        <span class="fir-mini-id">${f.fir_id}</span>
        <span class="severity-badge severity-${f.severity}">${f.severity}</span>
      </div>
      <div class="fir-mini-crime">${categoryBadge(f.crime_category)} ${f.crime_type}</div>
      <div class="fir-mini-meta">${f.police_station}, ${f.district} (${f.state_abbr || f.state}) · ${f.date}</div>
    </div>
  `).join('');
}

function renderMiniChart(analytics) {
  const ctx = document.getElementById('crime-chart');
  if (!ctx) return;
  const crimes = analytics.crime_types || {};
  const top = Object.entries(crimes).sort((a,b) => b[1]-a[1]).slice(0,8);

  destroyChart('crime-chart');
  State.charts['crime-chart'] = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: top.map(([k]) => k),
      datasets: [{
        data: top.map(([,v]) => v),
        backgroundColor: ['#ef4444','#f97316','#eab308','#22c55e','#3b82f6','#6366f1','#a855f7','#06b6d4'],
        borderWidth: 0,
        hoverOffset: 8,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: {
          position: 'right',
          labels: { color: '#8892a4', font: { size: 11, family: 'Inter' }, padding: 10, boxWidth: 12 }
        },
        tooltip: { callbacks: { label: ctx => ` ${ctx.label}: ${ctx.raw}` } }
      },
      animation: { duration: 800 }
    }
  });

  // Threat distribution chart
  const tCtx = document.getElementById('threat-chart');
  if (!tCtx) return;
  const dist = analytics.threat_distribution || {};
  destroyChart('threat-chart');
  State.charts['threat-chart'] = new Chart(tCtx, {
    type: 'bar',
    data: {
      labels: Object.keys(dist),
      datasets: [{
        label: 'Suspects',
        data: Object.values(dist),
        backgroundColor: ['#22c55e','#84cc16','#eab308','#f97316','#ef4444'],
        borderRadius: 6,
        borderSkipped: false,
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#4a5568', font: { size: 10 } } },
        y: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#4a5568', font: { size: 10 } } }
      },
      animation: { duration: 800 }
    }
  });
}

function renderLocationBars(locations) {
  const container = document.getElementById('location-bars');
  const entries = Object.entries(locations);
  const max = Math.max(...entries.map(([,v]) => v), 1);
  const colors = ['#ef4444','#f97316','#eab308','#22c55e','#3b82f6','#6366f1','#a855f7','#06b6d4','#ec4899','#14b8a6'];
  container.innerHTML = entries.map(([loc, count], i) => `
    <div class="loc-bar-item">
      <div class="loc-bar-header">
        <span class="loc-bar-name">${loc}</span>
        <span class="loc-bar-count">${count} FIRs</span>
      </div>
      <div class="loc-bar-track">
        <div class="loc-bar-fill" style="width:0%;background:${colors[i % colors.length]}" 
             data-target="${(count/max*100).toFixed(1)}"></div>
      </div>
    </div>
  `).join('');

  setTimeout(() => {
    document.querySelectorAll('.loc-bar-fill').forEach(el => {
      el.style.width = el.dataset.target + '%';
    });
  }, 100);
}

// ─── Mini Network Graph ───────────────────────────────────────────
async function loadMiniNetwork() {
  const data = await API.get('/api/graph');
  if (!data) return;

  const container = document.getElementById('mini-network');
  container.innerHTML = '';
  const w = container.clientWidth || 380;
  const h = 310;

  const svg = d3.select(container).append('svg')
    .attr('width', w).attr('height', h);

  const g = svg.append('g');

  // Use only top 25 nodes by degree
  const topNodes = data.nodes.sort((a,b) => b.degree - a.degree).slice(0, 25);
  const topIds = new Set(topNodes.map(n => n.id));
  const links = data.links.filter(l => topIds.has(l.source) && topIds.has(l.target)).slice(0, 40);

  const sim = d3.forceSimulation(topNodes)
    .force('link', d3.forceLink(links).id(d => d.id).distance(60))
    .force('charge', d3.forceManyBody().strength(-80))
    .force('center', d3.forceCenter(w/2, h/2))
    .force('collision', d3.forceCollide(15));

  const link = g.append('g').selectAll('line').data(links).enter().append('line')
    .attr('stroke', 'rgba(255,255,255,0.07)').attr('stroke-width', 1);

  const node = g.append('g').selectAll('circle').data(topNodes).enter().append('circle')
    .attr('r', d => 4 + d.threat_score * 8)
    .attr('fill', d => getNodeColor(d))
    .attr('fill-opacity', 0.85)
    .attr('stroke', d => getNodeColor(d))
    .attr('stroke-opacity', 0.4)
    .attr('stroke-width', 1.5);

  sim.on('tick', () => {
    link.attr('x1', d => d.source.x).attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x).attr('y2', d => d.target.y);
    node.attr('cx', d => d.x).attr('cy', d => d.y);
  });
}

// ─── Full D3 Network Graph ────────────────────────────────────────
async function loadGraph() {
  const data = await API.get('/api/graph');
  if (!data) return;
  State.graphData = data;
  renderGraph(data);
}

function renderGraph(data) {
  const container = document.getElementById('network-svg');
  const w = container.parentElement.clientWidth;
  const h = container.parentElement.clientHeight || 620;

  // Clear
  d3.select('#network-svg').selectAll('*').remove();

  const svg = d3.select('#network-svg').attr('width', w).attr('height', h);
  State.svg = svg;

  const g = svg.append('g');
  State.g = g;

  // Zoom
  const zoom = d3.zoom().scaleExtent([0.1, 4]).on('zoom', e => g.attr('transform', e.transform));
  svg.call(zoom);
  State.d3Zoom = zoom;

  // Tooltip
  const tooltip = document.getElementById('node-tooltip');

  // Assign community colors
  const communities = [...new Set(data.nodes.map(n => n.community))];
  const communityColors = d3.scaleOrdinal(d3.schemeTableau10).domain(communities);

  const simulation = d3.forceSimulation(data.nodes)
    .force('link', d3.forceLink(data.links).id(d => d.id).distance(d => 80 / (d.weight + 0.1)))
    .force('charge', d3.forceManyBody().strength(-120))
    .force('center', d3.forceCenter(w/2, h/2))
    .force('collision', d3.forceCollide(d => 6 + d.threat_score * 14));

  State.d3Simulation = simulation;

  // Links
  const link = g.append('g').attr('class', 'links').selectAll('line')
    .data(data.links).enter().append('line')
    .attr('class', 'graph-link')
    .attr('stroke-width', d => 0.5 + d.weight * 2)
    .attr('stroke-opacity', 0.4);

  // Node groups
  const node = g.append('g').attr('class', 'nodes').selectAll('g')
    .data(data.nodes).enter().append('g')
    .attr('class', 'graph-node')
    .call(d3.drag()
      .on('start', (e, d) => { if (!e.active) simulation.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
      .on('drag', (e, d) => { d.fx = e.x; d.fy = e.y; })
      .on('end', (e, d) => { if (!e.active) simulation.alphaTarget(0); d.fx = null; d.fy = null; })
    );

  // Circles
  node.append('circle')
    .attr('r', d => 6 + d.threat_score * 16)
    .attr('fill', d => {
      if (d.status === 'Fugitive') return '#a855f7';
      const baseColor = getNodeColor(d);
      return baseColor;
    })
    .attr('fill-opacity', 0.85)
    .attr('stroke', d => d.status === 'Fugitive' ? '#a855f7' : getNodeColor(d))
    .attr('stroke-opacity', 0.6)
    .attr('stroke-width', 1.5)
    .style('filter', d => d.threat_score > 0.6 ? 'url(#glow)' : 'none');

  // Labels
  node.append('text')
    .text(d => d.name.split(' ')[0])
    .attr('dy', d => -(7 + d.threat_score * 16) - 4)
    .attr('text-anchor', 'middle');

  // Glow filter
  const defs = svg.append('defs');
  const filter = defs.append('filter').attr('id', 'glow');
  filter.append('feGaussianBlur').attr('stdDeviation', '3').attr('result', 'coloredBlur');
  const feMerge = filter.append('feMerge');
  feMerge.append('feMergeNode').attr('in', 'coloredBlur');
  feMerge.append('feMergeNode').attr('in', 'SourceGraphic');

  // Tooltip interactions
  node.on('mouseover', function(e, d) {
    tooltip.innerHTML = `
      <div class="tooltip-name">${d.name}</div>
      ${d.alias ? `<div style="font-size:11px;color:#8892a4;margin-bottom:8px">"${d.alias}"</div>` : ''}
      <div class="tooltip-row"><span>Threat Score</span><span class="tooltip-val">${(d.threat_score*100).toFixed(0)}%</span></div>
      <div class="tooltip-row"><span>Role</span><span class="tooltip-val">${d.role || '—'}</span></div>
      <div class="tooltip-row"><span>Status</span><span class="tooltip-val">${d.status || '—'}</span></div>
      <div class="tooltip-row"><span>Location</span><span class="tooltip-val">${d.location || '—'}</span></div>
      <div class="tooltip-row"><span>Connections</span><span class="tooltip-val">${d.degree}</span></div>
      <div class="tooltip-row"><span>FIRs</span><span class="tooltip-val">${d.fir_count}</span></div>
    `;
    tooltip.classList.add('visible');
  })
  .on('mousemove', function(e) {
    const rect = document.getElementById('network-svg').parentElement.getBoundingClientRect();
    let x = e.clientX - rect.left + 12;
    let y = e.clientY - rect.top - 10;
    if (x + 240 > rect.width) x = e.clientX - rect.left - 240;
    tooltip.style.left = x + 'px';
    tooltip.style.top = y + 'px';
  })
  .on('mouseout', function() { tooltip.classList.remove('visible'); })
  .on('click', function(e, d) { openPersonModal(d.id); });

  // Tick
  simulation.on('tick', () => {
    link.attr('x1', d => d.source.x).attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x).attr('y2', d => d.target.y);
    node.attr('transform', d => `translate(${d.x},${d.y})`);
  });

  // Graph control buttons
  document.getElementById('zoom-in-btn').onclick = () => svg.transition().call(zoom.scaleBy, 1.4);
  document.getElementById('zoom-out-btn').onclick = () => svg.transition().call(zoom.scaleBy, 0.7);
  document.getElementById('fit-btn').onclick = () => svg.transition().call(zoom.transform, d3.zoomIdentity);

  // Threat filter slider
  document.getElementById('threat-filter').addEventListener('input', function() {
    document.getElementById('threat-filter-val').textContent = parseFloat(this.value).toFixed(1);
  });
}

async function applyGraphFilter() {
  const minThreat = document.getElementById('threat-filter').value;
  const data = await API.get(`/api/filter_graph?min_threat=${minThreat}`);
  if (data) renderGraph(data);
}

function resetGraphFilter() {
  document.getElementById('threat-filter').value = 0;
  document.getElementById('threat-filter-val').textContent = '0.0';
  if (State.graphData) renderGraph(State.graphData);
}

// ─── Suspects ─────────────────────────────────────────────────────
let allPersons = [];

async function loadSuspects() {
  const data = await API.get('/api/persons');
  allPersons = data || [];
  await loadMeta();
  renderSuspects(allPersons);
}

function filterSuspects() {
  const search = document.getElementById('suspect-search').value.toLowerCase();
  const role = document.getElementById('suspect-role').value;
  const status = document.getElementById('suspect-status').value;
  const stateF = document.getElementById('suspect-state').value;
  const sort = document.getElementById('suspect-sort').value;

  let filtered = allPersons;
  if (search) filtered = filtered.filter(p => p.name.toLowerCase().includes(search) || (p.alias||'').toLowerCase().includes(search) || p.id.toLowerCase().includes(search));
  if (role) filtered = filtered.filter(p => p.role === role);
  if (status) filtered = filtered.filter(p => p.status === status);
  if (stateF) filtered = filtered.filter(p => p.state === stateF);

  filtered = [...filtered].sort((a, b) => (b[sort] || 0) - (a[sort] || 0));
  renderSuspects(filtered);
}

function renderSuspects(persons) {
  const container = document.getElementById('suspects-grid');
  if (!persons.length) {
    container.innerHTML = '<div style="grid-column:1/-1;text-align:center;color:var(--text-muted);padding:40px">No suspects found</div>';
    return;
  }

  const colors = ['#ef4444','#f97316','#eab308','#22c55e','#3b82f6','#6366f1','#a855f7'];
  container.innerHTML = persons.map((p, i) => {
    const color = colors[i % colors.length];
    const score = p.computed_threat_score || 0;
    return `
      <div class="suspect-card ${getRiskClass(score)} status-${String(p.status).replace(/[^A-Za-z]/g,'')}" 
           onclick="openPersonModal('${p.id}')"
           style="animation-delay:${i * 0.03}s">
        <div class="suspect-card-header">
          <div class="suspect-avatar" style="border-color:${color};color:${color}">
            ${getAvatarLetters(p.name)}
          </div>
          <div class="suspect-card-info">
            <div class="suspect-card-name">${p.name}</div>
            <div class="suspect-card-meta">
              ${p.id} · <span>${p.role || 'Unknown'}</span> · ${p.district || p.location || '--'}, ${p.state || ''}
            </div>
          </div>
          <div class="threat-pill ${getThreatClass(score)}">${(score*100).toFixed(0)}%</div>
        </div>
        <div class="suspect-badge-row">
          <span class="tag ${statusClass(p.status)}">${p.status}</span>
          ${p.alias ? `<span class="tag">"${p.alias}"</span>` : ''}
          ${p.organization ? `<span class="tag" title="${p.organization}">${p.organization.split(' ').slice(0,2).join(' ')}</span>` : ''}
        </div>
        <div class="suspect-metrics">
          <div class="metric-box">
            <div class="metric-box-label">FIRs</div>
            <div class="metric-box-val" style="color:#ef4444">${p.fir_count || 0}</div>
          </div>
          <div class="metric-box">
            <div class="metric-box-label">PageRank</div>
            <div class="metric-box-val" style="color:#6366f1">${((p.pagerank||0)*100).toFixed(1)}</div>
          </div>
          <div class="metric-box">
            <div class="metric-box-label">Betweenness</div>
            <div class="metric-box-val" style="color:#f97316">${((p.betweenness_centrality||0)*100).toFixed(1)}</div>
          </div>
        </div>
      </div>
    `;
  }).join('');
}

// ─── Person Modal ─────────────────────────────────────────────────
async function openPersonModal(pid) {
  const data = await API.get(`/api/person/${pid}`);
  if (!data) return;

  const { person: p, firs, cdrs, transactions, neighbors } = data;
  const score = p.computed_threat_score || 0;

  document.getElementById('modal-content').innerHTML = `
    <div class="modal-person-header">
      <div class="modal-person-top">
        <div class="modal-avatar">${getAvatarLetters(p.name)}</div>
        <div>
          <div class="modal-person-name">${p.name}</div>
          <div class="modal-person-id">${p.id}</div>
          ${p.alias ? `<div class="modal-person-alias">Known as: "${p.alias}"</div>` : ''}
          <div style="display:flex;gap:6px;margin-top:8px">
            <span class="tag ${statusClass(p.status)}">${p.status}</span>
            <span class="threat-pill ${getThreatClass(score)}">${(score*100).toFixed(0)}% Threat</span>
          </div>
        </div>
      </div>
      <div class="modal-kpis">
        <div class="modal-kpi">
          <div class="modal-kpi-label">Threat Score</div>
          <div class="modal-kpi-val" style="color:#ef4444">${(score*100).toFixed(1)}%</div>
        </div>
        <div class="modal-kpi">
          <div class="modal-kpi-label">FIRs</div>
          <div class="modal-kpi-val" style="color:#f97316">${firs.length}</div>
        </div>
        <div class="modal-kpi">
          <div class="modal-kpi-label">CDRs</div>
          <div class="modal-kpi-val" style="color:#3b82f6">${cdrs.length}</div>
        </div>
        <div class="modal-kpi">
          <div class="modal-kpi-label">Connections</div>
          <div class="modal-kpi-val" style="color:#6366f1">${neighbors.length}</div>
        </div>
      </div>
    </div>

    <div class="modal-section">
      <div class="modal-section-title">Personal Information</div>
      <div class="modal-info-grid">
        <div class="modal-info-row"><div class="modal-info-key">Full Name</div><div class="modal-info-val">${p.name}</div></div>
        <div class="modal-info-row"><div class="modal-info-key">Date of Birth</div><div class="modal-info-val">${p.date_of_birth || '—'}</div></div>
        <div class="modal-info-row"><div class="modal-info-key">Gender</div><div class="modal-info-val">${p.gender || '—'}</div></div>
        <div class="modal-info-row"><div class="modal-info-key">Nationality</div><div class="modal-info-val">${p.nationality || '—'}</div></div>
        <div class="modal-info-row"><div class="modal-info-key">State</div><div class="modal-info-val">${p.state || '—'}</div></div>
        <div class="modal-info-row"><div class="modal-info-key">District</div><div class="modal-info-val">${p.district || p.location || '—'}</div></div>
        <div class="modal-info-row"><div class="modal-info-key">Locality</div><div class="modal-info-val">${p.neighborhood || '—'}</div></div>
        <div class="modal-info-row"><div class="modal-info-key">Home Police Station</div><div class="modal-info-val">${p.home_police_station || '—'}</div></div>
        <div class="modal-info-row"><div class="modal-info-key">History-sheeter</div><div class="modal-info-val">${p.history_sheeter ? 'Yes' : 'No'}</div></div>
        ${p.vehicle ? `<div class="modal-info-row"><div class="modal-info-key">Vehicle</div><div class="modal-info-val">${esc(p.vehicle)}</div></div>` : ''}
        ${p.identification_marks ? `<div class="modal-info-row"><div class="modal-info-key">Identification marks</div><div class="modal-info-val">${esc(p.identification_marks)}</div></div>` : ''}
        ${p.added_by ? `<div class="modal-info-row"><div class="modal-info-key">Added by</div><div class="modal-info-val">${esc(p.added_by)} · ${esc(p.added_on)}</div></div>` : ''}
        ${p.notes ? `<div class="modal-info-row" style="grid-column:1/-1"><div class="modal-info-key">Notes</div><div class="modal-info-val">${esc(p.notes)}</div></div>` : ''}
        <div class="modal-info-row"><div class="modal-info-key">Phone</div><div class="modal-info-val" style="font-family:'JetBrains Mono',monospace;font-size:12px">${p.phone || '—'}</div></div>
        <div class="modal-info-row"><div class="modal-info-key">Email</div><div class="modal-info-val" style="font-size:11px">${p.email || '—'}</div></div>
        <div class="modal-info-row"><div class="modal-info-key">Role</div><div class="modal-info-val">${p.role || '—'}</div></div>
        <div class="modal-info-row"><div class="modal-info-key">Organization</div><div class="modal-info-val">${p.organization || '—'}</div></div>
        <div class="modal-info-row"><div class="modal-info-key">Arrests</div><div class="modal-info-val" style="color:#ef4444">${p.arrest_count || 0}</div></div>
        <div class="modal-info-row"><div class="modal-info-key">Criminal History Score</div><div class="modal-info-val">${p.criminal_history || 0}/8</div></div>
      </div>
    </div>

    <div class="modal-section">
      <div class="modal-section-title">Graph Metrics</div>
      <div class="modal-info-grid">
        <div class="modal-info-row"><div class="modal-info-key">PageRank</div><div class="modal-info-val" style="color:#6366f1">${((p.pagerank||0)*100).toFixed(2)}</div></div>
        <div class="modal-info-row"><div class="modal-info-key">Betweenness Centrality</div><div class="modal-info-val" style="color:#f97316">${((p.betweenness_centrality||0)*100).toFixed(2)}</div></div>
        <div class="modal-info-row"><div class="modal-info-key">Degree Centrality</div><div class="modal-info-val" style="color:#3b82f6">${((p.degree_centrality||0)*100).toFixed(2)}</div></div>
        <div class="modal-info-row"><div class="modal-info-key">Closeness Centrality</div><div class="modal-info-val" style="color:#22c55e">${((p.closeness_centrality||0)*100).toFixed(2)}</div></div>
        <div class="modal-info-row"><div class="modal-info-key">Community ID</div><div class="modal-info-val">${p.community ?? '—'}</div></div>
        <div class="modal-info-row"><div class="modal-info-key">Total Transactions</div><div class="modal-info-val">${p.txn_count || 0}</div></div>
      </div>
    </div>

    ${firs.length ? `
    <div class="modal-section">
      <div class="modal-section-title">Related FIRs (${firs.length})</div>
      <div style="display:flex;flex-direction:column;gap:6px">
        ${firs.slice(0,5).map(f => `
          <div style="padding:10px 12px;background:var(--bg-surface);border:1px solid var(--border);border-radius:8px;cursor:pointer" onclick="openFIRModal('${f.fir_id}')">
            <div style="display:flex;justify-content:space-between;margin-bottom:4px">
              <span style="font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--indigo)">${f.fir_id}</span>
              <span class="severity-badge severity-${f.severity}">${f.severity}</span>
            </div>
            <div style="font-weight:600;font-size:13px;margin-bottom:2px">${categoryBadge(f.crime_category)} ${f.crime_type} <span style="font-weight:400;color:var(--text-muted);font-size:11px">u/s ${(f.sections||[]).join(', ')}</span></div>
            <div style="font-size:11px;color:var(--text-muted)">${f.police_station}, ${f.district} · ${f.date} · ${f.status}</div>
          </div>
        `).join('')}
      </div>
    </div>` : ''}

    ${neighbors.length ? `
    <div class="modal-section">
      <div class="modal-section-title">Known Associates (${neighbors.length})</div>
      <div style="display:flex;flex-wrap:wrap;gap:8px">
        ${neighbors.slice(0,15).map(n => `
          <div class="member-chip" onclick="closeModal();setTimeout(()=>openPersonModal('${n.id}'),100)">
            <div class="member-chip-dot"></div>${n.name || n.id}
          </div>
        `).join('')}
      </div>
    </div>` : ''}
  `;

  document.getElementById('modal-overlay').classList.add('active');
  document.getElementById('person-modal').classList.add('active');
}

function closeModal() {
  document.getElementById('modal-overlay').classList.remove('active');
  document.getElementById('person-modal').classList.remove('active');
}

// ─── FIRs ─────────────────────────────────────────────────────────
let allFIRs = [];

async function loadFIRs() {
  const [data] = await Promise.all([API.get('/api/firs'), loadMeta()]);
  allFIRs = data || [];
  filterFIRs();
}

function onFirStateChange() {
  const st = document.getElementById('fir-state').value;
  fillSelect('fir-district', st ? State.meta.states[st] : [], 'All Districts');
  filterFIRs();
}

function onFirCategoryChange() {
  fillSelect('fir-crime', allSubcategories(document.getElementById('fir-category').value), 'All Sub-categories');
  filterFIRs();
}

function filterFIRs() {
  const v = id => document.getElementById(id).value;
  const search = v('fir-search').toLowerCase();
  const filters = {
    state: v('fir-state'), district: v('fir-district'), crime_category: v('fir-category'),
    crime_type: v('fir-crime'), severity: v('fir-severity'), status: v('fir-status'),
  };

  let filtered = allFIRs;
  if (search) filtered = filtered.filter(f =>
    f.fir_id.toLowerCase().includes(search) || (f.cctns_id || '').includes(search) ||
    (f.police_station || '').toLowerCase().includes(search) ||
    (f.sections || []).some(x => x.toLowerCase().includes(search)) ||
    (f.accused_names || []).some(n => n.toLowerCase().includes(search)));
  Object.entries(filters).forEach(([k, val]) => {
    if (val) filtered = filtered.filter(f => f[k] === val);
  });
  document.getElementById('fir-count').textContent = `Showing ${filtered.length} of ${allFIRs.length} FIRs`;
  renderFIRs(filtered);
}

function renderFIRs(firs) {
  const tbody = document.getElementById('firs-tbody');
  if (!firs.length) {
    tbody.innerHTML = '<tr><td colspan="9" style="text-align:center;padding:30px;color:var(--text-muted)">No FIRs found</td></tr>';
    return;
  }
  tbody.innerHTML = firs.map(f => `
    <tr class="clickable-row" onclick="openFIRModal('${f.fir_id}')">
      <td class="mono">${f.fir_id}<div class="sub-mono">CCTNS ${f.cctns_id || ''}</div></td>
      <td style="white-space:nowrap">${f.date || '—'}</td>
      <td style="font-size:12px">${f.police_station}<div class="sub-text">${f.district}, ${f.state}</div></td>
      <td>${categoryBadge(f.crime_category)}</td>
      <td class="bold">${f.crime_type}<div class="sub-text">${(f.sections||[]).join(', ')} · ${f.crime_head}</div></td>
      <td style="font-size:12px;color:var(--text-secondary)">${(f.accused_names||[]).slice(0,2).join(', ')}${(f.accused_names||[]).length > 2 ? ` +${f.accused_names.length-2}` : ''}</td>
      <td><span class="severity-badge severity-${f.severity}">${f.severity}</span></td>
      <td style="font-size:11px;color:var(--text-muted)">${f.status}</td>
      <td style="font-family:'JetBrains Mono',monospace;font-size:11px">${f.amount_involved ? '₹' + fmt(f.amount_involved) : '—'}</td>
    </tr>
  `).join('');
}

async function openFIRModal(firId) {
  const data = await API.get(`/api/fir/${firId}`);
  if (!data) return;
  const { fir: f, crime: c, accused, lawful_actions } = data;
  const row = (k, v) => `<div class="modal-info-row"><div class="modal-info-key">${k}</div><div class="modal-info-val">${v ?? '—'}</div></div>`;
  document.getElementById('modal-content').innerHTML = `
    <div class="modal-person-header">
      <div class="modal-person-name" style="font-size:20px">FIR No. ${f.fir_no}</div>
      <div class="modal-person-id">${f.fir_id} · CCTNS ${f.cctns_id}</div>
      <div style="display:flex;gap:6px;margin-top:10px;flex-wrap:wrap">
        ${categoryBadge(f.crime_category)}
        <span class="severity-badge severity-${f.severity}">${f.severity}</span>
        <span class="tag">${f.law_regime}</span>
        <span class="tag">${f.cognizable ? 'Cognizable' : 'Non-cognizable'}</span>
        <span class="tag">${f.bailable ? 'Bailable' : 'Non-bailable'}</span>
      </div>
    </div>
    <div class="modal-section">
      <div class="modal-section-title">Registration</div>
      <div class="modal-info-grid">
        ${row('Police Station', f.police_station)}
        ${row('District', f.district)}
        ${row('State / UT', `${f.state} (code ${f.state_code})`)}
        ${row('Date / Time', `${f.date} ${f.time_of_occurrence || ''}`)}
        ${row('Place of occurrence', f.neighborhood)}
        ${row('Investigating Officer', f.io_name)}
        ${row('Complainant', f.complainant)}
        ${row('Status', f.status)}
      </div>
    </div>
    <div class="modal-section">
      <div class="modal-section-title">Offence</div>
      <div class="modal-info-grid">
        ${row('Category', f.crime_category)}
        ${row('NCRB crime head', f.crime_head)}
        ${row('Sub-category', f.crime_type)}
        ${row('Sections', (f.sections || []).join(', '))}
        ${row('Max punishment', f.max_punishment)}
        ${row('Triable by', f.triable_by)}
        ${row('Amount involved', f.amount_involved ? '₹' + Number(f.amount_involved).toLocaleString('en-IN') : '—')}
        ${row('Vehicle', f.vehicle_involved)}
      </div>
      <p style="font-size:12px;color:var(--text-secondary);margin-top:10px">${f.description}</p>
    </div>
    <div class="modal-section">
      <div class="modal-section-title">Possible lawful action</div>
      <ul class="action-list">${(lawful_actions || []).map(a => `<li>${esc(a)}</li>`).join('')}</ul>
      <button class="btn btn-sm btn-ghost" style="margin-top:8px" onclick="closeModal();switchTab('legal');selectLegalCrime('${esc(f.crime_category)}','${esc(f.crime_type)}')">Open in Lawful Action tab →</button>
    </div>
    <div class="modal-section">
      <div class="modal-section-title">Accused (${accused.length})</div>
      <div style="display:flex;flex-wrap:wrap;gap:8px">
        ${accused.map(a => `<div class="member-chip" onclick="closeModal();setTimeout(()=>openPersonModal('${a.id}'),100)"><div class="member-chip-dot"></div>${a.name}</div>`).join('')}
      </div>
    </div>`;
  document.getElementById('modal-overlay').classList.add('active');
  document.getElementById('person-modal').classList.add('active');
}

// ─── Transactions ─────────────────────────────────────────────────
async function loadTransactions() {
  const susp = document.getElementById('suspicious-only-txn')?.checked;
  const data = await API.get(`/api/transactions?suspicious=${susp}`);
  const all = data || [];

  // Update stats
  const allData = await API.get('/api/transactions');
  const allTxns = allData || [];
  document.getElementById('fin-total').textContent = allTxns.length;
  document.getElementById('fin-suspicious').textContent = allTxns.filter(t => t.suspicious).length;
  const largest = Math.max(...allTxns.map(t => t.amount || 0));
  document.getElementById('fin-largest').textContent = '₹' + fmt(largest);
  document.getElementById('fin-hawala').textContent = allTxns.filter(t => t.channel === 'Hawala').length;

  renderTransactions(all);
  renderChannelChart();
}

function renderTransactions(txns) {
  const tbody = document.getElementById('txn-tbody');
  if (!txns.length) {
    tbody.innerHTML = '<tr><td colspan="9" style="text-align:center;padding:30px;color:var(--text-muted)">No transactions</td></tr>';
    return;
  }
  tbody.innerHTML = txns.map(t => `
    <tr>
      <td class="mono">${t.txn_id}</td>
      <td style="font-size:11px">${t.date}</td>
      <td class="bold" style="font-size:12px">${t.sender_name}</td>
      <td class="bold" style="font-size:12px">${t.receiver_name}</td>
      <td style="font-family:'JetBrains Mono',monospace;font-size:12px;color:#22c55e">₹${fmt(t.amount)}</td>
      <td><span class="tag">${t.currency}</span></td>
      <td style="font-size:11px">${t.channel}</td>
      <td style="font-size:11px;color:var(--text-muted)">${t.purpose}</td>
      <td><span class="flag-suspicious ${t.suspicious ? 'flag-yes' : 'flag-no'}">${t.suspicious ? '⚠ Suspicious' : '✓ Clear'}</span></td>
    </tr>
  `).join('');
}

async function renderChannelChart() {
  const analytics = State.analyticsData || await API.get('/api/analytics');
  const channels = analytics?.transaction_channels || {};
  const ctx = document.getElementById('channel-chart');
  if (!ctx) return;

  destroyChart('channel-chart');
  State.charts['channel-chart'] = new Chart(ctx, {
    type: 'polarArea',
    data: {
      labels: Object.keys(channels),
      datasets: [{
        data: Object.values(channels),
        backgroundColor: ['rgba(239,68,68,0.7)','rgba(249,115,22,0.7)','rgba(234,179,8,0.7)','rgba(34,197,94,0.7)','rgba(59,130,246,0.7)','rgba(99,102,241,0.7)'],
        borderWidth: 0,
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { labels: { color: '#8892a4', font: { size: 11 } } } },
      scales: { r: { grid: { color: 'rgba(255,255,255,0.06)' }, ticks: { display: false } } }
    }
  });
}

// ─── CDRs ─────────────────────────────────────────────────────────
async function loadCDRs() {
  const susp = document.getElementById('suspicious-only-cdr')?.checked;
  const data = await API.get(`/api/cdrs?suspicious=${susp}`);
  renderCDRs(data || []);
}

function renderCDRs(cdrs) {
  const tbody = document.getElementById('cdr-tbody');
  if (!cdrs.length) {
    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;padding:30px;color:var(--text-muted)">No CDR records</td></tr>';
    return;
  }
  tbody.innerHTML = cdrs.map(c => `
    <tr>
      <td class="mono">${c.cdr_id}</td>
      <td style="font-size:11px;font-family:'JetBrains Mono',monospace">${c.datetime}</td>
      <td class="bold" style="font-size:12px">${c.caller_name}</td>
      <td class="bold" style="font-size:12px">${c.receiver_name}</td>
      <td style="font-family:'JetBrains Mono',monospace;font-size:11px">${Math.floor(c.duration_seconds/60)}m ${c.duration_seconds%60}s</td>
      <td><span class="tag">${c.call_type}</span></td>
      <td style="font-size:11px;color:var(--text-muted)">${c.tower_location}</td>
      <td><span class="flag-suspicious ${c.suspicious ? 'flag-yes' : 'flag-no'}">${c.suspicious ? '⚠' : '✓'}</span></td>
    </tr>
  `).join('');
}

// ─── Communities ──────────────────────────────────────────────────
async function loadCommunities() {
  const data = await API.get('/api/communities');
  renderCommunities(data || []);
}

function renderCommunities(communities) {
  const container = document.getElementById('communities-grid');
  if (!communities.length) {
    container.innerHTML = '<div style="text-align:center;color:var(--text-muted);padding:40px">No communities detected</div>';
    return;
  }

  container.innerHTML = communities.map((c, i) => {
    const score = c.avg_threat_score;
    const colors = ['#ef4444','#f97316','#eab308','#22c55e','#3b82f6','#6366f1','#a855f7','#06b6d4'];
    return `
      <div class="community-card ${c.high_risk ? 'high-risk' : ''}" style="animation-delay:${i*0.05}s">
        <div class="community-header">
          <span class="community-id">GROUP-${String(c.community_id).padStart(3,'0')}</span>
          <span class="community-size">${c.size} members</span>
        </div>
        <div class="community-threat">
          <div class="community-threat-bar">
            <div class="community-threat-fill" style="width:${score*100}%"></div>
          </div>
          <span style="font-size:11px;font-family:'JetBrains Mono',monospace;color:${score>0.5?'#ef4444':'#8892a4'};white-space:nowrap">
            ${(score*100).toFixed(0)}% risk
          </span>
        </div>
        <div class="community-members">
          ${c.members.slice(0,8).map((m, mi) => `
            <div class="member-chip" onclick="openPersonModal('${m.id}')">
              <div class="member-chip-dot" style="background:${colors[mi%colors.length]}"></div>
              ${m.name || m.id}
            </div>
          `).join('')}
          ${c.members.length > 8 ? `<div class="member-chip" style="color:var(--text-muted)">+${c.members.length-8} more</div>` : ''}
        </div>
      </div>
    `;
  }).join('');
}

// ─── Full Analytics ───────────────────────────────────────────────
const isoDate = d => d.toISOString().slice(0, 10);

async function loadAnalytics() {
  const m = await loadMeta();
  // Year presets come from the data
  const period = document.getElementById('an-period');
  if (m && !period.dataset.years) {
    const custom = period.querySelector('option[value="custom"]');
    m.years.forEach(y => custom.insertAdjacentHTML('beforebegin', `<option value="y${y}">Year ${y}</option>`));
    period.dataset.years = '1';
  }
  applyAnalyticsFilters();
}

function onPeriodChange() {
  const custom = document.getElementById('an-period').value === 'custom';
  document.querySelectorAll('.custom-range').forEach(el => el.classList.toggle('visible', custom));
  applyAnalyticsFilters();
}

function onAnalyticsStateChange() {
  const st = document.getElementById('an-state').value;
  const dist = document.getElementById('an-district');
  fillSelect('an-district', st ? State.meta.states[st] : [], 'All Districts');
  dist.disabled = !st;
  applyAnalyticsFilters();
}

function resetAnalyticsFilters() {
  ['an-state', 'an-district', 'an-category', 'an-start', 'an-end'].forEach(id => document.getElementById(id).value = '');
  document.getElementById('an-period').value = 'all';
  document.getElementById('an-district').disabled = true;
  onPeriodChange();
}

function periodRange() {
  const p = document.getElementById('an-period').value;
  // Relative periods count back from the latest FIR in the dataset
  const today = State.meta?.date_max ? new Date(State.meta.date_max) : new Date();
  const back = (days) => isoDate(new Date(today.getTime() - days * 86400000));
  if (p === '30d') return [back(30), isoDate(today)];
  if (p === '3m') return [back(91), isoDate(today)];
  if (p === '6m') return [back(182), isoDate(today)];
  if (p === '12m') return [back(365), isoDate(today)];
  if (p === 'post-bns') return ['2024-07-01', ''];
  if (p === 'pre-bns') return ['', '2024-06-30'];
  if (p.startsWith('y')) return [`${p.slice(1)}-01-01`, `${p.slice(1)}-12-31`];
  if (p === 'custom') return [document.getElementById('an-start').value, document.getElementById('an-end').value];
  return ['', ''];
}

async function applyAnalyticsFilters() {
  const [start, end] = periodRange();
  const params = new URLSearchParams();
  if (start) params.set('start', start);
  if (end) params.set('end', end);
  ['state', 'district', 'category'].forEach(k => {
    const val = document.getElementById(`an-${k}`).value;
    if (val) params.set(k, val);
  });
  const a = await API.get(`/api/analytics?${params}`);
  if (!a) return;

  const parts = [];
  if (start || end) parts.push(`${start || 'beginning'} → ${end || State.meta?.date_max || 'latest'}`);
  if (a.filters.state) parts.push(a.filters.state + (a.filters.district ? ` / ${a.filters.district}` : ''));
  if (a.filters.category) parts.push(a.filters.category + ' crimes');
  document.getElementById('an-filter-summary').textContent = parts.length ? 'Showing: ' + parts.join(' · ') : 'Showing: all FIRs';

  document.getElementById('an-kpi-firs').textContent = a.summary.firs;
  document.getElementById('an-kpi-heinous').textContent = a.summary.heinous;
  document.getElementById('an-kpi-accused').textContent = a.summary.accused;
  document.getElementById('an-kpi-amount').textContent = '₹' + fmt(a.summary.amount);
  renderAnalyticsCharts(a);
}

function renderAnalyticsCharts(a) {
  const chartCfg = { responsive: true, maintainAspectRatio: true, aspectRatio: 1.7, animation: { duration: 600 } };
  const gridColor = 'rgba(255,255,255,0.04)';
  const tickColor = '#4a5568';
  const legendColor = '#8892a4';
  const doughnutOpts = { ...chartCfg,
    plugins: { legend: { position: 'right', labels: { color: legendColor, font: { size: 11 }, padding: 12, boxWidth: 12 } } } };
  const hbarOpts = { ...chartCfg, indexAxis: 'y',
    plugins: { legend: { display: false } },
    scales: {
      x: { grid: { color: gridColor }, ticks: { color: tickColor, font: { size: 10 }, precision: 0 } },
      y: { grid: { display: false }, ticks: { color: '#8892a4', font: { size: 11 } } }
    } };
  const make = (id, config) => {
    destroyChart(id);
    State.charts[id] = new Chart(document.getElementById(id), config);
  };

  // Category doughnut
  const cats = a.crime_categories || {};
  make('analytics-category-chart', {
    type: 'doughnut',
    data: { labels: Object.keys(cats), datasets: [{ data: Object.values(cats),
      backgroundColor: ['#ef4444', '#f97316', '#eab308'], borderWidth: 0, hoverOffset: 8 }] },
    options: doughnutOpts,
  });

  // NCRB heads
  const heads = Object.entries(a.crime_heads || {});
  make('analytics-head-chart', {
    type: 'bar',
    data: { labels: heads.map(([k]) => k), datasets: [{ label: 'FIRs', data: heads.map(([, v]) => v),
      backgroundColor: 'rgba(168,85,247,0.7)', borderRadius: 6, borderSkipped: false }] },
    options: hbarOpts,
  });

  // Sub-categories
  const crimes = Object.entries(a.crime_types || {}).sort((x, y) => y[1] - x[1]).slice(0, 10);
  make('analytics-crime-chart', {
    type: 'bar',
    data: { labels: crimes.map(([k]) => k), datasets: [{ label: 'FIRs', data: crimes.map(([, v]) => v),
      backgroundColor: 'rgba(239,68,68,0.7)', borderRadius: 6, borderSkipped: false }] },
    options: hbarOpts,
  });

  // Monthly trend line
  const monthly = Object.entries(a.monthly_firs || {});
  make('analytics-monthly-chart', {
    type: 'line',
    data: {
      labels: monthly.map(([k]) => k),
      datasets: [{
        label: 'FIRs', data: monthly.map(([, v]) => v),
        borderColor: '#6366f1', backgroundColor: 'rgba(99,102,241,0.15)',
        borderWidth: 2, fill: true, tension: 0.4, pointRadius: 3, pointBackgroundColor: '#6366f1',
      }]
    },
    options: { ...chartCfg,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { color: gridColor }, ticks: { color: tickColor, font: { size: 10 }, maxRotation: 45 } },
        y: { grid: { color: gridColor }, ticks: { color: tickColor, font: { size: 10 }, precision: 0 } }
      }
    }
  });

  // Area bar: states, or districts when a state is selected
  document.getElementById('an-area-title').textContent =
    a.area_level === 'district' ? `FIRs by District (${a.filters.state})` : 'FIRs by State / UT';
  const locs = Object.entries(a.area_activity || {});
  make('analytics-location-chart', {
    type: 'bar',
    data: { labels: locs.map(([k]) => k), datasets: [{ label: 'FIRs', data: locs.map(([, v]) => v),
      backgroundColor: locs.map((_, i) => `hsl(${200 + i * 12},70%,55%)`), borderRadius: 6, borderSkipped: false }] },
    options: { ...chartCfg, aspectRatio: 3.4,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { display: false }, ticks: { color: '#8892a4', font: { size: 11 } } },
        y: { grid: { color: gridColor }, ticks: { color: tickColor, precision: 0 } }
      }
    }
  });

  const sev = a.severity || {};
  const sevOrder = ['Critical', 'High', 'Medium', 'Low'].filter(k => k in sev);
  make('analytics-severity-chart', {
    type: 'doughnut',
    data: { labels: sevOrder, datasets: [{ data: sevOrder.map(k => sev[k]),
      backgroundColor: ['#ef4444', '#f97316', '#eab308', '#22c55e'], borderWidth: 0, hoverOffset: 8 }] },
    options: doughnutOpts,
  });

  const stat = a.person_status || {};
  make('analytics-status-chart', {
    type: 'doughnut',
    data: { labels: Object.keys(stat), datasets: [{ data: Object.values(stat),
      backgroundColor: ['#22c55e', '#a855f7', '#3b82f6', '#06b6d4', '#eab308', '#64748b'], borderWidth: 0, hoverOffset: 8 }] },
    options: doughnutOpts,
  });

  const reg = a.law_regime || {};
  make('analytics-regime-chart', {
    type: 'doughnut',
    data: { labels: Object.keys(reg), datasets: [{ data: Object.values(reg),
      backgroundColor: ['#6366f1', '#06b6d4', '#f97316'], borderWidth: 0, hoverOffset: 8 }] },
    options: doughnutOpts,
  });

  // Hierarchy table
  const h = a.crime_hierarchy_counts || {};
  const el = document.getElementById('analytics-hierarchy');
  const cats3 = ['Heinous', 'Major', 'Minor'].filter(c => h[c]);
  el.innerHTML = cats3.length ? cats3.map(c => {
    const subs = Object.entries(h[c]).sort((x, y) => y[1] - x[1]);
    const total = subs.reduce((t, [, v]) => t + v, 0);
    return `<div class="hier-group">
      <div class="hier-head">${categoryBadge(c)}<span>${total} FIRs</span></div>
      ${subs.map(([k, v]) => `<div class="hier-row"><span>${k}</span><span class="mono">${v}</span></div>`).join('')}
    </div>`;
  }).join('') : '<div style="color:var(--text-muted);padding:20px">No FIRs match these filters</div>';
}

// ─── Lawful Action ────────────────────────────────────────────────
async function loadLegal() {
  const data = await API.get('/api/legal');
  if (!data) return;
  State.legal = data;

  document.getElementById('law-grid').innerHTML = data.laws.map(l => `
    <a class="law-card" href="${l.url}" target="_blank" rel="noopener">
      <div class="law-short">${l.short}</div>
      <div class="law-name">${l.name}</div>
      ${l.replaces ? `<div class="law-replaces">Replaced: ${l.replaces}</div>` : ''}
      <div class="law-summary">${l.summary}</div>
      <div class="law-meta">${l.type} · ${l.in_force} <span class="law-link">Official text ↗</span></div>
    </a>`).join('');

  document.getElementById('procedure-list').innerHTML = data.procedure.map(p => `
    <li><div class="proc-step">${p.step} <span class="proc-law">${p.law}</span></div><div class="proc-detail">${p.detail}</div></li>`).join('');

  document.getElementById('helpline-row').innerHTML = data.helplines.map(h => `
    <a class="helpline" href="tel:${h.number}"><span class="helpline-num">${h.number}</span><span>${h.name}</span></a>`).join('');
  document.getElementById('portal-list').innerHTML = data.portals.map(p => `
    <li><a href="${p.url}" target="_blank" rel="noopener">${p.name} ↗</a><span>${p.url.replace(/^https?:\/\//, '').replace(/\/$/, '')}</span></li>`).join('');

  const cats = Object.keys(data.category_info);
  fillSelect('legal-category', cats, null);
  onLegalCategoryChange();
  loadNews();
}

function onLegalCategoryChange() {
  const cat = document.getElementById('legal-category').value;
  fillSelect('legal-crime', State.legal.crime_catalog.filter(c => c.category === cat).map(c => c.sub), null);
  renderLegalCrime();
}

function selectLegalCrime(category, sub) {
  const apply = () => {
    document.getElementById('legal-category').value = category;
    onLegalCategoryChange();
    document.getElementById('legal-crime').value = sub;
    renderLegalCrime();
  };
  if (State.legal) apply();
  else { State.legalLoaded = true; loadLegal().then(apply); }
}

function renderLegalCrime() {
  const sub = document.getElementById('legal-crime').value;
  const c = State.legal.crime_catalog.find(x => x.sub === sub);
  const el = document.getElementById('legal-crime-detail');
  if (!c) { el.innerHTML = ''; return; }
  const actions = State.legal.head_actions[c.head] || [];
  const seven = c.category === 'Heinous' || /7 years|10 years|14 years|life/i.test(c.punishment);
  const row = (k, v) => `<div class="modal-info-row"><div class="modal-info-key">${k}</div><div class="modal-info-val">${v || '—'}</div></div>`;
  el.innerHTML = `
    <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px">
      ${categoryBadge(c.category)}<span class="tag">${c.head}</span>
      <span class="tag">${c.cognizable ? 'Cognizable' : 'Non-cognizable'}</span>
      <span class="tag">${c.bailable ? 'Bailable' : 'Non-bailable'}</span>
    </div>
    <div class="modal-info-grid">
      ${row('BNS 2023 section', c.bns)}
      ${row('Old IPC section', c.ipc)}
      ${row('Special Act', c.sll)}
      ${row('Punishment', c.punishment)}
      ${row('Triable by', c.court)}
      ${row('Category rule', State.legal.category_info[c.category])}
    </div>
    <div class="modal-section-title" style="margin-top:16px">Possible lawful action</div>
    <ul class="action-list">
      <li>Register FIR under BNSS s.173 (Zero FIR / e-FIR allowed)${c.ipc && c.bns ? `; use ${c.ipc} if the offence was committed before 1 July 2024, ${c.bns} after` : ''}.</li>
      <li>${seven ? 'Punishable with 7 years or more: forensic team visit mandatory (BNSS s.176(3)); arrest without warrant permitted on BNSS s.35 grounds.' : 'Punishable with less than 7 years: notice of appearance under BNSS s.35(3) unless arrest is necessary.'}</li>
      <li>${c.bailable ? 'Bail is a right (BNSS s.478).' : 'Bail is at the court\'s discretion (BNSS s.480); anticipatory bail lies under s.482.'}</li>
      ${actions.map(x => `<li>${x}</li>`).join('')}
    </ul>
    <div style="margin-top:10px;display:flex;gap:8px;flex-wrap:wrap">
      ${(c.acts || []).map(a => `<span class="tag">${a}</span>`).join('')}
      <button class="btn btn-sm btn-ghost" onclick="showFIRsFor('${c.category}','${c.sub}')">View matching FIRs →</button>
    </div>`;
}

async function showFIRsFor(category, sub) {
  switchTab('firs');
  await loadMeta();
  if (!allFIRs.length) { allFIRs = (await API.get('/api/firs')) || []; State.firsLoaded = true; }
  document.getElementById('fir-category').value = category;
  fillSelect('fir-crime', allSubcategories(category), 'All Sub-categories');
  document.getElementById('fir-crime').value = sub;
  filterFIRs();
}

async function loadNews() {
  const topic = document.getElementById('news-topic').value;
  const el = document.getElementById('news-list');
  el.innerHTML = '<div class="loading-spinner"></div>';
  const data = await API.get(`/api/news?topic=${encodeURIComponent(topic)}`);
  if (!data) { el.innerHTML = '<div style="color:var(--text-muted)">Could not load news</div>'; return; }
  const note = data.live ? '' : `<div class="news-offline">Live news unavailable (no internet from the server). Official sources below.</div>`;
  el.innerHTML = note + data.items.map(n => `
    <a class="news-item" href="${esc(n.link)}" target="_blank" rel="noopener noreferrer">
      <div class="news-title">${esc(n.title)}</div>
      <div class="news-meta">${esc(n.source)}${n.published ? ' · ' + esc(new Date(n.published).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })) : ''}</div>
    </a>`).join('');
}

// ─── Add Record ───────────────────────────────────────────────────
async function initRecordForm() {
  const m = await loadMeta();
  if (!m) return;
  fillSelect('rec-state', Object.keys(m.states).sort(), null);
  fillSelect('rec-role', m.roles, null);
  fillSelect('rec-org', m.organizations, 'None / unknown');
  onRecordStateChange();
  await refreshRecordLists();
}

async function refreshRecordLists() {
  const [persons, firs] = await Promise.all([API.get('/api/persons?sort=name'), API.get('/api/firs')]);
  const sel = document.getElementById('rec-associates');
  sel.innerHTML = (persons || []).sort((a, b) => a.name.localeCompare(b.name))
    .map(p => `<option value="${p.id}">${esc(p.name)} (${p.id}, ${esc(p.district || '')})</option>`).join('');
  document.getElementById('rec-firs').innerHTML = (firs || [])
    .map(f => `<option value="${esc(f.fir_id)}">${esc(f.crime_type)} · ${esc(f.police_station)}</option>`).join('');
  renderRecentRecords();
}

function onRecordStateChange(district) {
  const st = document.getElementById('rec-state').value;
  fillSelect('rec-district', State.meta.states[st] || [], null);
  if (district) document.getElementById('rec-district').value = district;
  onRecordDistrictChange();
}

function onRecordDistrictChange(ps) {
  const d = document.getElementById('rec-district').value;
  fillSelect('rec-ps', State.meta.police_stations[d] || [], 'Not known');
  if (ps) document.getElementById('rec-ps').value = ps;
  document.getElementById('rec-localities').innerHTML =
    (State.meta.localities[d] || []).map(l => `<option value="${esc(l)}">`).join('');
}

function readRecordForm() {
  const form = document.getElementById('record-form');
  const fd = new FormData(form);
  const rec = {};
  for (const [k, v] of fd.entries()) if (k !== 'associate_ids') rec[k] = v;
  rec.associate_ids = [...document.getElementById('rec-associates').selectedOptions].map(o => o.value);
  rec.contact_numbers = (rec.contact_numbers || '').split(',').map(x => x.trim()).filter(Boolean);
  rec.history_sheeter = form.elements.history_sheeter.checked;
  return rec;
}

function writeRecordForm(rec) {
  const form = document.getElementById('record-form');
  form.reset();
  form.elements.state.value = rec.state;
  onRecordStateChange(rec.district);
  onRecordDistrictChange(rec.home_police_station);
  Object.entries(rec).forEach(([k, v]) => {
    const el = form.elements[k];
    if (!el || ['state', 'district', 'home_police_station', 'associate_ids'].includes(k)) return;
    if (el.type === 'checkbox') el.checked = !!v;
    else el.value = Array.isArray(v) ? v.join(', ') : (v ?? '');
  });
}

function resetRecordForm() {
  document.getElementById('record-form').reset();
  onRecordStateChange();
  document.getElementById('links-title').textContent = 'Link analysis';
  document.getElementById('links-panel').innerHTML = '<div class="empty-hint">Form cleared.</div>';
}

async function fillSampleRecord() {
  if (!State.recordFormReady) { await initRecordForm(); State.recordFormReady = true; }
  const rec = await API.get('/api/records/sample');
  if (rec) writeRecordForm(rec);
  document.getElementById('links-title').textContent = 'Link analysis';
  document.getElementById('links-panel').innerHTML =
    '<div class="empty-hint">Sample filled in. Press <b>Check links</b> to preview, or <b>Save record</b> to add this person.</div>';
}

async function previewLinks() {
  const res = await API.post('/api/records/check', readRecordForm());
  if (res.ok) renderLinks(res.data, null);
}

async function saveRecord(e) {
  e.preventDefault();
  const btn = document.getElementById('rec-save');
  btn.disabled = true; btn.textContent = 'Saving & analysing…';
  const res = await API.post('/api/records', readRecordForm());
  btn.disabled = false; btn.textContent = 'Save record';
  if (!res.ok) {
    document.getElementById('links-panel').innerHTML = `<div class="form-error">${esc(res.data?.error || 'Could not save')}</div>`;
    return;
  }
  renderLinks(res.data.links, res.data.person);
  document.getElementById('main-content').scrollTo({ top: 0, behavior: 'smooth' });
  document.getElementById('tab-addrecord').scrollTo?.({ top: 0, behavior: 'smooth' });
  // Other tabs must reload to show the new person
  Object.assign(State, { graphLoaded: false, suspectsLoaded: false, firsLoaded: false, commLoaded: false,
                         analyticsLoaded: false, analyticsData: null, meta: null });
  allPersons = []; allFIRs = [];
  loadDashboard();
  document.getElementById('record-form').reset();
  await loadMeta();
  onRecordStateChange();
  refreshRecordLists();
}

function renderLinks(links, person) {
  const panel = document.getElementById('links-panel');
  const title = document.getElementById('links-title');
  const head = person ? `
    <div class="saved-banner">
      <div><b>${esc(person.name)}</b> saved as <span class="mono">${person.id}</span></div>
      <div class="saved-meta">Threat score ${(person.computed_threat_score * 100).toFixed(0)}% · ${links.length} link(s) added to the network</div>
      <div style="display:flex;gap:8px;margin-top:8px">
        <button class="btn btn-sm btn-ghost" onclick="openPersonModal('${person.id}')">View profile</button>
        <button class="btn btn-sm btn-ghost" onclick="switchTab('network')">View in network graph</button>
      </div>
    </div>` : '';
  title.textContent = person ? 'Related people found' : 'Link preview (not saved yet)';
  if (!links.length) {
    panel.innerHTML = head + '<div class="empty-hint">No links found with people on record.</div>';
    return;
  }
  const strong = links.filter(l => l.score >= 0.7).length;
  panel.innerHTML = head + `
    <div class="links-summary">${links.length} related ${links.length === 1 ? 'person' : 'people'} · ${strong} strong link(s)</div>
    ${links.map(l => `
      <div class="link-card" onclick="openPersonModal('${l.person.id}')">
        <div class="link-top">
          <div>
            <div class="link-name">${esc(l.person.name)} <span class="mono">${l.person.id}</span></div>
            <div class="link-meta">${esc(l.relationship_type)} · ${esc(l.person.district || '')}, ${esc(l.person.state || '')}${l.person.organization ? ' · ' + esc(l.person.organization) : ''}</div>
          </div>
          <span class="threat-pill ${getThreatClass(l.score)}">${(l.score * 100).toFixed(0)}%</span>
        </div>
        <ul class="link-reasons">${l.reasons.map(r => `<li>${esc(r)}</li>`).join('')}</ul>
      </div>`).join('')}`;
}

async function renderRecentRecords() {
  const data = await API.get('/api/records');
  const el = document.getElementById('recent-records');
  if (!data || !data.length) { el.innerHTML = '<div class="empty-hint">No records added yet.</div>'; return; }
  el.innerHTML = data.slice(0, 8).map(p => `
    <div class="suspect-mini-item" onclick="openPersonModal('${p.id}')">
      <div class="suspect-mini-avatar" style="border-color:#22c55e;color:#22c55e">${getAvatarLetters(p.name)}</div>
      <div class="suspect-mini-info">
        <div class="suspect-mini-name">${esc(p.name)}</div>
        <div class="suspect-mini-role">${p.id} · ${esc(p.district)} · ${(p.known_associates || []).length} links · by ${esc(p.added_by)} ${esc(p.added_on || '')}</div>
      </div>
      <div class="threat-pill ${getThreatClass(p.computed_threat_score || 0)}">${((p.computed_threat_score || 0) * 100).toFixed(0)}%</div>
    </div>`).join('');
}

// ─── Investigations ───────────────────────────────────────────────
async function loadInvestigationBadge() {
  const data = await API.get('/api/investigations');
  if (!data) return;
  const b = document.getElementById('badge-overdue');
  b.textContent = data.summary.overdue;
  b.title = 'Chargesheets overdue';
  b.style.display = data.summary.overdue ? '' : 'none';
}

async function loadInvestigations() {
  const [data] = await Promise.all([API.get('/api/investigations'), loadMeta()]);
  if (!data) return;
  State.inv = data;
  const s = data.summary;
  document.getElementById('inv-kpi-open').textContent = s.open;
  document.getElementById('inv-kpi-overdue').textContent = s.overdue;
  document.getElementById('inv-kpi-due').textContent = s.due_15;
  document.getElementById('inv-kpi-cs').textContent = s.chargesheeted;
  fillSelect('inv-state', Object.keys(State.meta.states).sort(), 'All States');
  fillSelect('inv-stage', data.stages, 'All Stages');
  const newSel = document.getElementById('inv-new-fir');
  newSel.innerHTML = '<option value="">Select FIR without an investigation…</option>' +
    data.firs_without_case.map(f => `<option value="${esc(f.fir_id)}">${esc(f.fir_id)} · ${esc(f.crime_type)}</option>`).join('');
  renderInvestigations();
}

function deadlineCell(c) {
  if (c.stage_index >= 5) return '<span class="dl dl-done">Filed</span>';
  if (!c.chargesheet_due) return '<span class="dl">Clock starts on arrest</span>';
  const d = c.days_to_deadline;
  const cls = d < 0 ? 'dl-over' : d <= 15 ? 'dl-soon' : 'dl-ok';
  const txt = d < 0 ? `${-d} days overdue` : `${d} days left`;
  return `<span class="dl ${cls}">${txt}</span><div class="sub-text">${c.chargesheet_due} (${c.deadline_days}-day limit)</div>`;
}

function renderInvestigations() {
  if (!State.inv) return;
  const q = document.getElementById('inv-search').value.toLowerCase();
  const st = document.getElementById('inv-state').value;
  const stage = document.getElementById('inv-stage').value;
  const pr = document.getElementById('inv-priority').value;
  const od = document.getElementById('inv-overdue').checked;
  const items = State.inv.items.filter(c =>
    (!q || [c.case_id, c.fir_id, c.io_name, ...(c.accused_names || [])].some(x => (x || '').toLowerCase().includes(q))) &&
    (!st || c.state === st) && (!stage || c.stage === stage) && (!pr || c.priority === pr) && (!od || c.overdue));
  const tbody = document.getElementById('inv-tbody');
  if (!items.length) { tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:30px;color:var(--text-muted)">No investigations match</td></tr>'; return; }
  tbody.innerHTML = items.map(c => `
    <tr class="clickable-row" onclick="openInvestigation('${c.case_id}')">
      <td class="mono">${c.case_id}<div class="sub-text">opened ${c.opened_on} · ${c.days_open} days</div></td>
      <td><div class="bold">${esc(c.crime_type)}</div><div class="sub-mono">${esc(c.fir_id)}</div></td>
      <td style="font-size:12px">${esc(c.police_station)}<div class="sub-text">${esc(c.district)}, ${esc(c.state)}</div></td>
      <td style="font-size:12px">${esc(c.io_name)}</td>
      <td style="min-width:170px"><div style="font-size:12px;font-weight:600">${esc(c.stage)}</div>
        <div class="progress-track"><div class="progress-fill" style="width:${c.progress}%"></div></div></td>
      <td>${deadlineCell(c)}</td>
      <td><span class="prio prio-${c.priority.slice(0, 2)}">${esc(c.priority)}</span></td>
    </tr>`).join('');
}

function openInvestigation(caseId) {
  const c = State.inv.items.find(x => x.case_id === caseId);
  if (!c) return;
  const stages = State.inv.stages;
  document.getElementById('modal-content').innerHTML = `
    <div class="modal-person-header">
      <div class="modal-person-name" style="font-size:20px">${c.case_id}</div>
      <div class="modal-person-id">FIR ${esc(c.fir_id)} · ${esc(c.police_station)}, ${esc(c.district)}</div>
      <div style="display:flex;gap:6px;margin-top:10px;flex-wrap:wrap">
        ${categoryBadge(c.crime_category)}<span class="tag">${esc(c.crime_type)}</span>
        <span class="prio prio-${c.priority.slice(0, 2)}">${esc(c.priority)}</span><span class="tag">${c.status}</span>
      </div>
    </div>
    <div class="modal-section">
      <div class="modal-section-title">Progress</div>
      <div class="stepper">${stages.map((s, i) => `<div class="step ${i < c.stage_index ? 'done' : i === c.stage_index ? 'current' : ''}"><span class="step-dot">${i < c.stage_index ? '✓' : i + 1}</span><span class="step-label">${s}</span></div>`).join('')}</div>
      <div class="modal-info-grid" style="margin-top:14px">
        <div class="modal-info-row"><div class="modal-info-key">Investigating officer</div><div class="modal-info-val">${esc(c.io_name)}</div></div>
        <div class="modal-info-row"><div class="modal-info-key">Sections</div><div class="modal-info-val">${esc((c.sections || []).join(', '))}</div></div>
        <div class="modal-info-row"><div class="modal-info-key">Arrest date</div><div class="modal-info-val">${c.arrest_date || 'Not arrested yet'}</div></div>
        <div class="modal-info-row"><div class="modal-info-key">Chargesheet deadline</div><div class="modal-info-val">${deadlineCell(c)}</div></div>
      </div>
    </div>
    ${c.next_actions.length ? `<div class="modal-section"><div class="modal-section-title">Next actions</div>
      <ul class="action-list">${c.next_actions.map(a => `<li>${esc(a)}</li>`).join('')}</ul></div>` : ''}
    <div class="modal-section">
      <div class="modal-section-title">Add update</div>
      <div class="form-grid">
        <label class="form-field">Move to stage<select id="inv-upd-stage" class="filter-select">${stages.map((s, i) => `<option value="${i}" ${i === c.stage_index ? 'selected' : ''}>${s}</option>`).join('')}</select></label>
        <label class="form-field">Arrest date (if arrested)<input type="date" id="inv-upd-arrest" value="${c.arrest_date || ''}" ${c.arrest_date ? 'disabled' : ''} /></label>
        <label class="form-field span-2">Note<textarea id="inv-upd-note" rows="2" placeholder="e.g. FSL report received; 2 accused arrested"></textarea></label>
      </div>
      <div class="form-actions"><button class="btn btn-primary" onclick="submitInvestigationUpdate('${c.case_id}')">Save update</button></div>
    </div>
    <div class="modal-section">
      <div class="modal-section-title">Timeline</div>
      <div class="timeline">${[...c.updates].reverse().map(u => `
        <div class="tl-item"><div class="tl-date">${u.date}</div><div><div class="tl-stage">${esc(u.stage)}</div><div class="tl-note">${esc(u.note)}</div><div class="tl-by">${esc(u.by)}</div></div></div>`).join('')}</div>
    </div>
    <div class="modal-section">
      <div class="modal-section-title">Accused</div>
      <div style="display:flex;flex-wrap:wrap;gap:8px">${c.accused_ids.map((id, i) => `<div class="member-chip" onclick="closeModal();setTimeout(()=>openPersonModal('${id}'),100)"><div class="member-chip-dot"></div>${esc(c.accused_names[i] || id)}</div>`).join('')}</div>
    </div>`;
  document.getElementById('modal-overlay').classList.add('active');
  document.getElementById('person-modal').classList.add('active');
}

async function submitInvestigationUpdate(caseId) {
  const res = await API.post(`/api/investigations/${caseId}/update`, {
    stage_index: Number(document.getElementById('inv-upd-stage').value),
    note: document.getElementById('inv-upd-note').value,
    arrest_date: document.getElementById('inv-upd-arrest').value || null,
  });
  if (!res.ok) { alert(res.data?.error || 'Could not save update'); return; }
  await loadInvestigations();
  loadInvestigationBadge();
  openInvestigation(caseId);
}

async function openNewInvestigation() {
  const firId = document.getElementById('inv-new-fir').value;
  if (!firId) { alert('Select an FIR first'); return; }
  const res = await API.post('/api/investigations', { fir_id: firId });
  if (!res.ok) { alert(res.data?.error || 'Could not open investigation'); return; }
  await loadInvestigations();
  openInvestigation(res.data.case_id);
}

// ─── Global Search ────────────────────────────────────────────────
let searchTimeout = null;
const searchInput = document.getElementById('global-search-input');
const searchResults = document.getElementById('search-results');

searchInput.addEventListener('input', () => {
  clearTimeout(searchTimeout);
  const q = searchInput.value.trim();
  if (q.length < 2) { searchResults.classList.remove('visible'); return; }
  searchTimeout = setTimeout(async () => {
    const data = await API.get(`/api/search?q=${encodeURIComponent(q)}`);
    renderSearchResults(data || []);
  }, 300);
});

searchInput.addEventListener('blur', () => {
  setTimeout(() => searchResults.classList.remove('visible'), 200);
});

function renderSearchResults(results) {
  if (!results.length) { searchResults.classList.remove('visible'); return; }
  searchResults.innerHTML = results.map(r => `
    <div class="search-result-item" onclick="handleSearchResult('${r.type}','${r.id}')">
      <span class="search-result-type">${r.type}</span>
      <div>
        <div class="search-result-label">${r.label}</div>
        <div class="search-result-sub">${r.sublabel}</div>
      </div>
    </div>
  `).join('');
  searchResults.classList.add('visible');
}

function handleSearchResult(type, id) {
  searchResults.classList.remove('visible');
  searchInput.value = '';
  if (type === 'person') { openPersonModal(id); }
  else if (type === 'fir') { openFIRModal(id); }
}

// ─── Chart Utilities ──────────────────────────────────────────────
function destroyChart(id) {
  if (State.charts[id]) { State.charts[id].destroy(); delete State.charts[id]; }
}

// Chart.js global defaults
Chart.defaults.color = '#8892a4';
Chart.defaults.font.family = 'Inter';

// ─── Refresh ──────────────────────────────────────────────────────
function refreshAll() {
  State.graphLoaded = false;
  State.suspectsLoaded = false;
  State.firsLoaded = false;
  State.financialLoaded = false;
  State.cdrLoaded = false;
  State.commLoaded = false;
  State.analyticsLoaded = false;
  State.analyticsData = null;
  State.legalLoaded = false;
  loadDashboard();
  const btn = document.getElementById('refresh-btn');
  btn.style.opacity = '0.5';
  setTimeout(() => btn.style.opacity = '1', 1200);
}

// ─── Initialize ───────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  loadDashboard();
  loadMeta();
  loadInvestigationBadge();
  // Close search on outside click
  document.addEventListener('click', e => {
    if (!e.target.closest('.global-search')) {
      searchResults.classList.remove('visible');
    }
  });
});
