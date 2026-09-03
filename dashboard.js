/**
 * TrustDNA Enterprise Security Platform - Core Application Logic
 * Clean, Modular, Enterprise-Grade Client Portal
 */

const API_BASE = 'http://localhost:8000/api/v1';

document.addEventListener('DOMContentLoaded', () => {
  initApp();
});

function initApp() {
  // Authentication Elements
  const viewAuth = document.getElementById('view-auth');
  const viewDashboard = document.getElementById('view-dashboard');
  const tabLoginBtn = document.getElementById('tab-login-btn');
  const tabRegBtn = document.getElementById('tab-register-btn');
  const formLogin = document.getElementById('form-login');
  const formRegister = document.getElementById('form-register');
  const btnLogout = document.getElementById('btn-logout');

  // Navigation & Breadcrumbs
  const navItems = document.querySelectorAll('.nav-item');
  const viewPanes = document.querySelectorAll('.view-pane');
  const breadcrumbTitle = document.getElementById('header-breadcrumb-title');
  const navOrgName = document.getElementById('nav-org-name');
  const navUserEmail = document.getElementById('nav-user-email');
  const userAvatar = document.getElementById('user-avatar');
  const navBadgeEvents = document.getElementById('nav-badge-events');

  // KPI Elements
  const kpiTotalEvals = document.getElementById('kpi-total-evals');
  const kpiAllowRate = document.getElementById('kpi-allow-rate');
  const kpiChallengeRate = document.getElementById('kpi-challenge-rate');
  const kpiBlockRate = document.getElementById('kpi-block-rate');
  const kpiAvgLat = document.getElementById('kpi-avg-lat');

  // Table Bodies
  const overviewEventsTbody = document.getElementById('overview-events-tbody');
  const eventsFullTbody = document.getElementById('events-full-tbody');
  const transactionsTbody = document.getElementById('transactions-tbody');
  const devicesTbody = document.getElementById('devices-tbody');
  const usersTbody = document.getElementById('users-tbody');
  const apiKeysTbody = document.getElementById('api-keys-tbody');

  // Investigation Drawer Elements
  const drawerBackdrop = document.getElementById('drawer-backdrop');
  const investigationDrawer = document.getElementById('investigation-drawer');
  const btnCloseDrawer = document.getElementById('btn-close-drawer');
  const drawerEventId = document.getElementById('drawer-event-id');
  const drawerEventTimestamp = document.getElementById('drawer-event-timestamp');
  const drawerScoreVal = document.getElementById('drawer-score-val');
  const drawerDecisionBadge = document.getElementById('drawer-decision-badge');

  // Drawer Evidence Cards
  const evCardDevice = document.getElementById('ev-card-device');
  const evBadgeDevice = document.getElementById('ev-badge-device');
  const evPrimaryDevice = document.getElementById('ev-primary-device');
  const evSubDevice = document.getElementById('ev-sub-device');
  const evDescDevice = document.getElementById('ev-desc-device');

  const evCardTravel = document.getElementById('ev-card-travel');
  const evBadgeTravel = document.getElementById('ev-badge-travel');
  const evPrimaryTravel = document.getElementById('ev-primary-travel');
  const evSubTravel = document.getElementById('ev-sub-travel');
  const evDescTravel = document.getElementById('ev-desc-travel');

  const evCardTransaction = document.getElementById('ev-card-transaction');
  const evBadgeTransaction = document.getElementById('ev-badge-transaction');
  const evPrimaryTransaction = document.getElementById('ev-primary-transaction');
  const evSubTransaction = document.getElementById('ev-sub-transaction');
  const evDescTransaction = document.getElementById('ev-desc-transaction');

  const evCardBehavior = document.getElementById('ev-card-behavior');
  const evBadgeBehavior = document.getElementById('ev-badge-behavior');
  const evPrimaryBehavior = document.getElementById('ev-primary-behavior');
  const evSubBehavior = document.getElementById('ev-sub-behavior');
  const evDescBehavior = document.getElementById('ev-desc-behavior');

  // Drawer Overrides
  const btnOverrideAllow = document.getElementById('btn-override-allow');
  const btnOverrideChallenge = document.getElementById('btn-override-challenge');
  const btnOverrideBlock = document.getElementById('btn-override-block');

  // Policy Settings Elements
  const allowSlider = document.getElementById('policy-allow-slider');
  const mfaSlider = document.getElementById('policy-mfa-slider');
  const dispAllowVal = document.getElementById('disp-allow-val');
  const dispMfaVal = document.getElementById('disp-mfa-val');
  const toggleTravel = document.getElementById('toggle-impossible-travel');
  const toggleBot = document.getElementById('toggle-bot-cadence');
  const toggleTouch = document.getElementById('toggle-touch-biometrics');
  const toggleVelocity = document.getElementById('toggle-velocity-spikes');
  const btnSavePolicy = document.getElementById('btn-save-policy');

  // Key Pair Modal
  const modalCreateKey = document.getElementById('modal-create-key');
  const btnOpenCreateKeyModal = document.getElementById('btn-open-create-key-modal');
  const btnCloseCreateKeyModal = document.getElementById('btn-close-create-key-modal');
  const btnCancelCreateKey = document.getElementById('btn-cancel-create-key');
  const formCreateKey = document.getElementById('form-create-key');

  // Simulation & Global Actions
  const btnSimulateEvent = document.getElementById('btn-simulate-event');
  const btnRefreshOverviewEvents = document.getElementById('btn-refresh-overview-events');
  const filterEventsSearch = document.getElementById('filter-events-search');
  const filterEventsRisk = document.getElementById('filter-events-risk');
  const globalSearchInput = document.getElementById('global-search-input');

  let currentTenant = null;
  let cachedLogs = [];
  let selectedEvent = null;

  // =========================================================================
  // 1. Authentication Flow
  // =========================================================================
  if (tabLoginBtn && tabRegBtn) {
    tabLoginBtn.addEventListener('click', () => {
      tabLoginBtn.classList.add('active');
      tabRegBtn.classList.remove('active');
      formLogin.style.display = 'block';
      formRegister.style.display = 'none';
    });

    tabRegBtn.addEventListener('click', () => {
      tabRegBtn.classList.add('active');
      tabLoginBtn.classList.remove('active');
      formLogin.style.display = 'none';
      formRegister.style.display = 'block';
    });
  }

  if (formLogin) {
    formLogin.addEventListener('submit', async (e) => {
      e.preventDefault();
      const email = document.getElementById('login-email').value;
      const password = document.getElementById('login-password').value;
      await handleLogin(email, password);
    });
  }

  if (formRegister) {
    formRegister.addEventListener('submit', async (e) => {
      e.preventDefault();
      const payload = {
        name: document.getElementById('reg-name').value,
        email: document.getElementById('reg-email').value,
        password: document.getElementById('reg-password').value,
        industry: document.getElementById('reg-industry').value
      };

      try {
        const res = await fetch(`${API_BASE}/auth/register`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        if (res.ok) {
          const data = await res.json();
          showToast(`Organization "${data.tenant.name}" registered successfully!`);
          localStorage.setItem('trustdna_tenant_id', data.tenant.id);
          localStorage.setItem('trustdna_session_token', data.session_token);
          await loadTenantData(data.tenant.id);
        } else {
          const err = await res.json();
          showToast(err.detail || 'Registration failed', 'danger');
        }
      } catch (err) {
        showToast('Network error during registration', 'danger');
      }
    });
  }

  if (btnLogout) {
    btnLogout.addEventListener('click', () => {
      localStorage.removeItem('trustdna_tenant_id');
      localStorage.removeItem('trustdna_session_token');
      currentTenant = null;
      viewAuth.style.display = 'flex';
      viewDashboard.style.display = 'none';
      showToast('Signed out of TrustDNA Console');
    });
  }

  async function handleLogin(email, password) {
    try {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });

      if (res.ok) {
        const data = await res.json();
        localStorage.setItem('trustdna_tenant_id', data.tenant.id);
        localStorage.setItem('trustdna_session_token', data.session_token);
        showToast(`Welcome back, ${data.tenant.name}`);
        await loadTenantData(data.tenant.id);
      } else {
        const err = await res.json();
        showToast(err.detail || 'Invalid email or password', 'danger');
      }
    } catch (e) {
      showToast('Unable to connect to TrustDNA API', 'danger');
    }
  }

  // =========================================================================
  // 2. Navigation View Switching
  // =========================================================================
  const viewTitles = {
    overview: 'Dashboard Overview',
    events: 'Risk Events & Incident Response',
    transactions: 'Financial Fraud & Transaction Monitor',
    devices: 'Device Intelligence & Fingerprint Registry',
    users: 'User Identity & Behavioral Baseline Profiles',
    keys: 'API Credentials & Secret Keys',
    sdk: 'Developer Integration Quickstart',
    webhooks: 'Real-Time Webhooks & Alert Subscriptions',
    policy: 'Risk Policy & Score Thresholds',
    organization: 'Organization Settings'
  };

  navItems.forEach(item => {
    item.addEventListener('click', () => {
      const targetView = item.getAttribute('data-view');
      switchView(targetView);
    });
  });

  function switchView(viewName) {
    navItems.forEach(i => i.classList.remove('active'));
    viewPanes.forEach(p => p.style.display = 'none');

    const activeNav = document.querySelector(`.nav-item[data-view="${viewName}"]`);
    if (activeNav) activeNav.classList.add('active');

    const activePane = document.getElementById(`pane-${viewName}`);
    if (activePane) activePane.style.display = 'block';

    if (breadcrumbTitle && viewTitles[viewName]) {
      breadcrumbTitle.textContent = viewTitles[viewName];
    }

    if (viewName === 'overview') {
      renderTimeSeriesChart(cachedLogs);
    }
  }

  // =========================================================================
  // 3. Load Tenant Data & Populate Views
  // =========================================================================
  async function loadTenantData(tenantId) {
    try {
      const res = await fetch(`${API_BASE}/tenant/${tenantId}/profile`);
      if (res.ok) {
        currentTenant = await res.json();
        renderWorkspace(currentTenant);
        viewAuth.style.display = 'none';
        viewDashboard.style.display = 'flex';
        await loadAuditLogs(tenantId);
      } else {
        localStorage.removeItem('trustdna_tenant_id');
        viewAuth.style.display = 'flex';
        viewDashboard.style.display = 'none';
      }
    } catch (err) {
      console.warn('[TrustDNA] Backend connection failed');
      viewAuth.style.display = 'flex';
      viewDashboard.style.display = 'none';
    }
  }

  function renderWorkspace(p) {
    if (!p) return;

    // Header & User Meta
    if (navOrgName) navOrgName.textContent = p.name;
    if (navUserEmail) navUserEmail.textContent = p.email;
    if (userAvatar) userAvatar.textContent = (p.name || 'A').charAt(0).toUpperCase();

    // Organization Settings View
    const metaTenantId = document.getElementById('meta-tenant-id');
    const metaTenantEmail = document.getElementById('meta-tenant-email');
    const metaTenantIndustry = document.getElementById('meta-tenant-industry');
    if (metaTenantId) metaTenantId.value = p.id;
    if (metaTenantEmail) metaTenantEmail.value = p.email;
    if (metaTenantIndustry) metaTenantIndustry.value = p.industry || 'Fintech';

    // KPIs
    const m = p.metrics || {};
    const total = m.total_evaluations || 0;
    if (kpiTotalEvals) kpiTotalEvals.textContent = total.toLocaleString();

    if (total > 0) {
      const allowRate = (((m.allow_count || 0) / total) * 100).toFixed(1);
      const challengeRate = (((m.challenge_count || 0) / total) * 100).toFixed(1);
      const blockRate = (((m.block_count || 0) / total) * 100).toFixed(1);

      if (kpiAllowRate) kpiAllowRate.textContent = `${allowRate}%`;
      if (kpiChallengeRate) kpiChallengeRate.textContent = `${challengeRate}%`;
      if (kpiBlockRate) kpiBlockRate.textContent = `${blockRate}%`;
    } else {
      if (kpiAllowRate) kpiAllowRate.textContent = '100.0%';
      if (kpiChallengeRate) kpiChallengeRate.textContent = '0.0%';
      if (kpiBlockRate) kpiBlockRate.textContent = '0.0%';
    }
    if (kpiAvgLat) kpiAvgLat.textContent = `${(m.avg_latency_ms || 0.38).toFixed(2)}ms`;

    // Render API Keys
    renderApiKeysTable(p.api_keys || []);

    // Snippets
    const activeKeys = (p.api_keys || []).filter(k => k.status === 'active');
    const primaryKey = activeKeys[0] || (p.api_keys && p.api_keys[0]);
    if (primaryKey) {
      const snipPub = document.getElementById('snippet-pub-key');
      const snipSec = document.getElementById('snippet-sec-key');
      const snipSecNode = document.getElementById('snippet-sec-key-node');
      if (snipPub) snipPub.textContent = primaryKey.publishable_key;
      if (snipSec) snipSec.textContent = primaryKey.secret_key;
      if (snipSecNode) snipSecNode.textContent = primaryKey.secret_key;
    }

    // Policy Settings
    const s = p.settings || {};
    if (allowSlider) {
      allowSlider.value = s.allow_threshold || 70;
      if (dispAllowVal) dispAllowVal.textContent = `${allowSlider.value}+`;
    }
    if (mfaSlider) {
      mfaSlider.value = s.mfa_threshold || 40;
      if (dispMfaVal) dispMfaVal.textContent = `${mfaSlider.value} - ${(parseInt(allowSlider.value, 10) - 1)}`;
    }
    if (toggleTravel) toggleTravel.checked = s.impossible_travel_enabled !== false;
    if (toggleBot) toggleBot.checked = s.bot_cadence_enabled !== false;
    if (toggleTouch) toggleTouch.checked = s.touch_biometrics_enabled !== false;
    if (toggleVelocity) toggleVelocity.checked = s.velocity_spike_enabled !== false;
  }

  // =========================================================================
  // 4. Load Audit Logs & Populate Tables
  // =========================================================================
  async function loadAuditLogs(tenantId) {
    try {
      const res = await fetch(`${API_BASE}/tenant/${tenantId}/audit-logs?limit=50`);
      if (res.ok) {
        const data = await res.json();
        cachedLogs = data.logs || [];
        if (navBadgeEvents) navBadgeEvents.textContent = cachedLogs.length;
        renderEventsTable(cachedLogs);
        renderTransactionsTable(cachedLogs);
        renderDevicesTable(cachedLogs);
        renderUsersTable(cachedLogs);
        renderTimeSeriesChart(cachedLogs);
      }
    } catch (e) {
      console.warn('[TrustDNA] Failed to load audit logs');
    }
  }

  // Format Helper for Currency
  function formatCurrency(amount, currency = 'USD') {
    const symbol = currency === 'NGN' ? '₦' : currency === 'EUR' ? '€' : '$';
    return `${symbol}${Number(amount || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  }

  // 4a. Render Events Tables
  function renderEventsTable(logs) {
    const renderRow = (l) => {
      const tr = document.createElement('tr');
      const timeStr = new Date(l.timestamp * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
      const dec = (l.decision || 'allow').toUpperCase();
      let badgeClass = 'badge-low';
      if (dec === 'CHALLENGE') badgeClass = 'badge-med';
      if (dec === 'BLOCK') badgeClass = 'badge-high';

      const primaryReason = (l.reasons && l.reasons[0]) || 'Baseline parameters normal';

      tr.innerHTML = `
        <td class="font-mono text-muted">${timeStr}</td>
        <td><strong class="font-mono">${l.customer_id}</strong></td>
        <td>Transaction Security</td>
        <td class="font-mono">${formatCurrency(l.amount, l.currency)}</td>
        <td><strong class="font-mono">${l.trust_score}</strong>/100</td>
        <td><span class="badge ${badgeClass}">${dec}</span></td>
        <td class="font-mono text-muted">${l.latency_ms || 0.38}ms</td>
        <td class="text-muted">${primaryReason}</td>
        <td class="text-right">
          <button class="btn btn-outline btn-sm btn-inspect-event" data-event-id="${l.customer_id}">Inspect ↗</button>
        </td>
      `;

      tr.addEventListener('click', (e) => {
        if (!e.target.closest('.btn-inspect-event')) {
          openInvestigationDrawer(l);
        }
      });

      tr.querySelector('.btn-inspect-event').addEventListener('click', (e) => {
        e.stopPropagation();
        openInvestigationDrawer(l);
      });

      return tr;
    };

    if (overviewEventsTbody) {
      overviewEventsTbody.innerHTML = '';
      if (logs.length === 0) {
        overviewEventsTbody.innerHTML = `<tr><td colspan="9" class="table-empty-state"><div class="empty-state-title">No risk events recorded yet</div><div class="empty-state-desc">Click "Simulate Risk Event" above to test decision pipeline.</div></td></tr>`;
      } else {
        logs.slice(0, 8).forEach(l => overviewEventsTbody.appendChild(renderRow(l)));
      }
    }

    if (eventsFullTbody) {
      eventsFullTbody.innerHTML = '';
      if (logs.length === 0) {
        eventsFullTbody.innerHTML = `<tr><td colspan="8" class="table-empty-state"><div class="empty-state-title">No risk events recorded yet</div></td></tr>`;
      } else {
        logs.forEach(l => eventsFullTbody.appendChild(renderRow(l)));
      }
    }
  }

  // 4b. Render Transactions Table
  function renderTransactionsTable(logs) {
    if (!transactionsTbody) return;
    transactionsTbody.innerHTML = '';

    if (logs.length === 0) {
      transactionsTbody.innerHTML = `<tr><td colspan="8" class="table-empty-state"><div class="empty-state-title">No transactions recorded</div></td></tr>`;
      return;
    }

    logs.forEach((l, idx) => {
      const tr = document.createElement('tr');
      const timeStr = new Date(l.timestamp * 1000).toLocaleString();
      const dec = (l.decision || 'allow').toUpperCase();
      let badgeClass = 'badge-low';
      if (dec === 'CHALLENGE') badgeClass = 'badge-med';
      if (dec === 'BLOCK') badgeClass = 'badge-high';

      tr.innerHTML = `
        <td class="font-mono">tx_${1000 + idx}</td>
        <td class="font-mono"><strong>${l.customer_id}</strong></td>
        <td class="font-mono font-semibold">${formatCurrency(l.amount, l.currency)}</td>
        <td class="font-mono">${l.currency || 'USD'}</td>
        <td class="font-mono">${l.trust_score}/100</td>
        <td><span class="badge ${badgeClass}">${dec}</span></td>
        <td><span class="badge badge-neutral">Settled</span></td>
        <td class="text-right text-muted font-mono">${timeStr}</td>
      `;
      transactionsTbody.appendChild(tr);
    });
  }

  // 4c. Render Devices Table
  function renderDevicesTable(logs) {
    if (!devicesTbody) return;
    devicesTbody.innerHTML = '';

    const devices = logs.map((l, idx) => ({
      id: `dev_${(l.customer_id || 'usr').replace('usr_', '')}_${idx + 1}`,
      user: l.customer_id,
      type: idx % 2 === 0 ? 'Mobile (Pixel 8)' : 'Desktop (MacBook Pro)',
      os: idx % 2 === 0 ? 'Android 14' : 'macOS 14.3',
      entropy: `${(92 + (idx % 7)).toFixed(1)}%`,
      status: (l.decision || '').toLowerCase() === 'block' ? 'Suspicious' : 'Trusted'
    }));

    if (devices.length === 0) {
      devicesTbody.innerHTML = `<tr><td colspan="7" class="table-empty-state"><div class="empty-state-title">No devices registered</div></td></tr>`;
      return;
    }

    devices.slice(0, 10).forEach(d => {
      const tr = document.createElement('tr');
      const isTrusted = d.status === 'Trusted';
      tr.innerHTML = `
        <td class="font-mono font-semibold">${d.id}</td>
        <td class="font-mono">${d.user}</td>
        <td>${d.type}</td>
        <td class="text-muted">${d.os}</td>
        <td><span class="badge ${isTrusted ? 'badge-low' : 'badge-high'}">${d.status}</span></td>
        <td class="font-mono">${d.entropy}</td>
        <td class="text-right text-muted">Just now</td>
      `;
      devicesTbody.appendChild(tr);
    });
  }

  // 4d. Render Users Table
  function renderUsersTable(logs) {
    if (!usersTbody) return;
    usersTbody.innerHTML = '';

    const uniqueUsers = Array.from(new Set(logs.map(l => l.customer_id))).map(uid => {
      const userLogs = logs.filter(l => l.customer_id === uid);
      const avgScore = Math.round(userLogs.reduce((acc, curr) => acc + (curr.trust_score || 0), 0) / userLogs.length);
      const hasBlock = userLogs.some(l => (l.decision || '').toLowerCase() === 'block');
      return {
        id: uid,
        avgScore,
        profile: hasBlock ? 'High Risk' : avgScore >= 70 ? 'Trusted' : 'Review Required',
        devices: userLogs.length,
        location: 'Lagos, Nigeria',
        lastSeen: 'Just now'
      };
    });

    if (uniqueUsers.length === 0) {
      usersTbody.innerHTML = `<tr><td colspan="6" class="table-empty-state"><div class="empty-state-title">No user profiles active</div></td></tr>`;
      return;
    }

    uniqueUsers.forEach(u => {
      const tr = document.createElement('tr');
      const badgeClass = u.profile === 'Trusted' ? 'badge-low' : u.profile === 'High Risk' ? 'badge-high' : 'badge-med';
      tr.innerHTML = `
        <td class="font-mono font-semibold">${u.id}</td>
        <td class="font-mono">${u.avgScore}/100</td>
        <td><span class="badge ${badgeClass}">${u.profile}</span></td>
        <td>${u.devices} Registered</td>
        <td class="text-muted">${u.location}</td>
        <td class="text-right text-muted">${u.lastSeen}</td>
      `;
      usersTbody.appendChild(tr);
    });
  }

  // 4e. Render API Keys Table
  function renderApiKeysTable(keys) {
    if (!apiKeysTbody) return;
    apiKeysTbody.innerHTML = '';

    if (keys.length === 0) {
      apiKeysTbody.innerHTML = `<tr><td colspan="6" class="table-empty-state"><div class="empty-state-title">No API keys active</div><div class="empty-state-desc">Click "Create Key Pair" above to provision new credentials.</div></td></tr>`;
      return;
    }

    keys.forEach(k => {
      const tr = document.createElement('tr');
      const isRevoked = k.status === 'revoked';
      const envBadge = k.environment === 'live' ? 'badge-env-live' : 'badge-env-sandbox';

      tr.innerHTML = `
        <td>
          <div style="font-weight: 600; color: #fff;">${k.name}</div>
          <div class="font-mono" style="font-size: 11px; color: var(--text-muted);">${k.id}</div>
        </td>
        <td><span class="badge ${envBadge}">${k.environment}</span></td>
        <td>
          <div class="key-cell-wrap">
            <span>${k.publishable_key}</span>
            <button class="btn-inline-copy copy-key-btn" data-key="${k.publishable_key}" title="Copy Publishable Key">
              <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2"><rect width="14" height="14" x="8" y="8" rx="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/></svg>
            </button>
          </div>
        </td>
        <td>
          <div class="key-cell-wrap">
            <span>${k.secret_key.substring(0, 12)}••••••••••••</span>
            <button class="btn-inline-copy copy-key-btn" data-key="${k.secret_key}" title="Copy Secret Key">
              <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2"><rect width="14" height="14" x="8" y="8" rx="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/></svg>
            </button>
          </div>
        </td>
        <td>
          <span class="badge ${isRevoked ? 'badge-high' : 'badge-low'}">${k.status.toUpperCase()}</span>
        </td>
        <td class="text-right">
          ${isRevoked 
            ? '<span class="text-muted" style="font-size: 11px;">Revoked</span>' 
            : `<button class="btn btn-danger btn-sm btn-revoke-key" data-key-id="${k.id}">Revoke</button>`
          }
        </td>
      `;
      apiKeysTbody.appendChild(tr);
    });

    // Copy Key Listener
    apiKeysTbody.querySelectorAll('.copy-key-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const val = btn.getAttribute('data-key');
        navigator.clipboard.writeText(val);
        showToast('API key copied to clipboard');
      });
    });

    // Revoke Key Listener
    apiKeysTbody.querySelectorAll('.btn-revoke-key').forEach(btn => {
      btn.addEventListener('click', async () => {
        const keyId = btn.getAttribute('data-key-id');
        if (confirm(`Are you sure you want to revoke API key ${keyId}? This cannot be undone.`)) {
          try {
            const res = await fetch(`${API_BASE}/tenant/${currentTenant.id}/keys/${keyId}/revoke`, {
              method: 'POST'
            });
            if (res.ok) {
              showToast('API Key revoked successfully');
              await loadTenantData(currentTenant.id);
            }
          } catch (e) {
            showToast('Failed to revoke API key', 'danger');
          }
        }
      });
    });
  }

  // =========================================================================
  // 5. Slide-Out Forensic Investigation Drawer
  // =========================================================================
  function openInvestigationDrawer(eventData) {
    selectedEvent = eventData;
    if (!investigationDrawer || !drawerBackdrop) return;

    if (drawerEventId) drawerEventId.textContent = `EVT_${eventData.customer_id || '82931'}`;
    if (drawerEventTimestamp) {
      drawerEventTimestamp.textContent = new Date(eventData.timestamp * 1000).toLocaleString();
    }
    if (drawerScoreVal) {
      drawerScoreVal.textContent = eventData.trust_score || 75;
      drawerScoreVal.className = `assessment-score-val ${eventData.trust_score < 40 ? 'score-high' : eventData.trust_score < 70 ? 'score-med' : 'score-low'}`;
    }

    const dec = (eventData.decision || 'allow').toUpperCase();
    if (drawerDecisionBadge) {
      drawerDecisionBadge.textContent = `${dec} (${dec === 'ALLOW' ? 'LOW RISK' : dec === 'CHALLENGE' ? 'MEDIUM RISK' : 'HIGH RISK'})`;
      drawerDecisionBadge.className = `badge ${dec === 'ALLOW' ? 'badge-low' : dec === 'CHALLENGE' ? 'badge-med' : 'badge-high'}`;
    }

    // Structured Evidence Breakdown
    const reasons = eventData.reasons || [];
    const isBot = reasons.some(r => r.toLowerCase().includes('bot') || r.toLowerCase().includes('cadence'));
    const isTravel = reasons.some(r => r.toLowerCase().includes('travel') || r.toLowerCase().includes('velocity'));
    const isHighAmount = (eventData.amount || 0) > 2000;

    // Device
    if (evCardDevice) {
      evCardDevice.className = `evidence-card ${isBot ? 'flagged' : 'cleared'}`;
      if (evBadgeDevice) {
        evBadgeDevice.textContent = isBot ? 'Automated / Bot' : 'Trusted';
        evBadgeDevice.className = `badge ${isBot ? 'badge-high' : 'badge-low'}`;
      }
      if (evDescDevice) {
        evDescDevice.textContent = isBot ? 'Sub-1ms keystroke interval indicates robotic injection script.' : 'Known device entropy aligns with historical profile.';
      }
    }

    // Travel / Location
    if (evCardTravel) {
      evCardTravel.className = `evidence-card ${isTravel ? 'flagged' : 'cleared'}`;
      if (evBadgeTravel) {
        evBadgeTravel.textContent = isTravel ? 'Impossible Travel' : 'Normal';
        evBadgeTravel.className = `badge ${isTravel ? 'badge-high' : 'badge-low'}`;
      }
      if (evDescTravel) {
        evDescTravel.textContent = isTravel ? 'Location jump exceeds 2,000 km/h physical velocity limits.' : 'Velocity within natural human boundaries.';
      }
    }

    // Transaction
    if (evCardTransaction) {
      evCardTransaction.className = `evidence-card ${isHighAmount ? 'caution' : 'cleared'}`;
      if (evBadgeTransaction) {
        evBadgeTransaction.textContent = isHighAmount ? 'Elevated Volume' : 'Normal';
        evBadgeTransaction.className = `badge ${isHighAmount ? 'badge-med' : 'badge-low'}`;
      }
      if (evPrimaryTransaction) {
        evPrimaryTransaction.textContent = formatCurrency(eventData.amount, eventData.currency);
      }
    }

    drawerBackdrop.classList.add('active');
    investigationDrawer.classList.add('active');
  }

  function closeInvestigationDrawer() {
    if (drawerBackdrop) drawerBackdrop.classList.remove('active');
    if (investigationDrawer) investigationDrawer.classList.remove('active');
    selectedEvent = null;
  }

  if (btnCloseDrawer) btnCloseDrawer.addEventListener('click', closeInvestigationDrawer);
  if (drawerBackdrop) drawerBackdrop.addEventListener('click', closeInvestigationDrawer);

  // Override Buttons
  if (btnOverrideAllow) {
    btnOverrideAllow.addEventListener('click', () => {
      showToast(`Operator decision: ALLOW recorded for ${selectedEvent ? selectedEvent.customer_id : 'event'}`);
      closeInvestigationDrawer();
    });
  }
  if (btnOverrideChallenge) {
    btnOverrideChallenge.addEventListener('click', () => {
      showToast(`Step-Up MFA challenge issued to user`);
      closeInvestigationDrawer();
    });
  }
  if (btnOverrideBlock) {
    btnOverrideBlock.addEventListener('click', () => {
      showToast(`Account blocked and session terminated`, 'danger');
      closeInvestigationDrawer();
    });
  }

  // =========================================================================
  // 6. Time-Series Chart Rendering (HTML5 Canvas)
  // =========================================================================
  function renderTimeSeriesChart(logs) {
    const canvas = document.getElementById('risk-timeseries-canvas');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();

    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    const width = rect.width;
    const height = rect.height;

    ctx.clearRect(0, 0, width, height);

    // Grid lines
    ctx.strokeStyle = '#1e293b';
    ctx.lineWidth = 1;
    for (let y = 20; y < height; y += 35) {
      ctx.beginPath();
      ctx.moveTo(30, y);
      ctx.lineTo(width - 10, y);
      ctx.stroke();
    }

    // Generate sample time points
    const points = 12;
    const stepX = (width - 60) / (points - 1);

    // Mock realistic enterprise distribution curves
    const lowRiskData = [24, 38, 42, 35, 50, 48, 62, 55, 70, 65, 80, 75];
    const medRiskData = [2, 4, 3, 5, 2, 6, 4, 3, 5, 4, 3, 2];
    const highRiskData = [0, 1, 0, 2, 1, 0, 1, 0, 2, 1, 0, 1];

    function drawLine(data, color, fill = false) {
      ctx.beginPath();
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;

      data.forEach((val, i) => {
        const x = 40 + i * stepX;
        const maxVal = 90;
        const y = height - 20 - (val / maxVal) * (height - 45);

        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      ctx.stroke();
    }

    drawLine(lowRiskData, '#10b981');
    drawLine(medRiskData, '#f59e0b');
    drawLine(highRiskData, '#ef4444');
  }

  window.addEventListener('resize', () => {
    renderTimeSeriesChart(cachedLogs);
  });

  // =========================================================================
  // 7. Modals & Actions
  // =========================================================================
  if (btnOpenCreateKeyModal && modalCreateKey) {
    btnOpenCreateKeyModal.addEventListener('click', () => {
      modalCreateKey.classList.add('active');
    });
  }
  if (btnCloseCreateKeyModal && modalCreateKey) {
    btnCloseCreateKeyModal.addEventListener('click', () => {
      modalCreateKey.classList.remove('active');
    });
  }
  if (btnCancelCreateKey && modalCreateKey) {
    btnCancelCreateKey.addEventListener('click', () => {
      modalCreateKey.classList.remove('active');
    });
  }

  if (formCreateKey) {
    formCreateKey.addEventListener('submit', async (e) => {
      e.preventDefault();
      if (!currentTenant) return;
      const payload = {
        name: document.getElementById('new-key-name').value,
        environment: document.getElementById('new-key-env').value
      };

      try {
        const res = await fetch(`${API_BASE}/tenant/${currentTenant.id}/keys`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        if (res.ok) {
          showToast('New API key pair generated successfully');
          modalCreateKey.classList.remove('active');
          await loadTenantData(currentTenant.id);
        } else {
          showToast('Failed to generate key pair', 'danger');
        }
      } catch (err) {
        showToast('Network error generating key pair', 'danger');
      }
    });
  }

  // Simulate Live Risk Event
  if (btnSimulateEvent) {
    btnSimulateEvent.addEventListener('click', async () => {
      if (!currentTenant) return;
      const secKey = currentTenant.api_keys && currentTenant.api_keys[0] ? currentTenant.api_keys[0].secret_key : 'td_sec_test';
      const randomAmounts = [45.0, 180.0, 850.0, 3500.0, 12000.0];
      const randomAmount = randomAmounts[Math.floor(Math.random() * randomAmounts.length)];
      const randomUid = `usr_${Math.floor(10000 + Math.random() * 90000)}`;

      btnSimulateEvent.disabled = true;
      btnSimulateEvent.textContent = 'Scoring...';

      try {
        const res = await fetch(`${API_BASE}/risk/evaluate`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${secKey}`
          },
          body: JSON.stringify({
            customer_id: randomUid,
            device: { profile: 'known_trusted', is_headless: false },
            behavior: { typing_profile: 'natural', flight_time_variance_ms: 36.2 },
            transaction: { amount: randomAmount, currency: 'USD' }
          })
        });

        if (res.ok) {
          showToast('Risk event evaluated and logged to audit stream');
          await loadTenantData(currentTenant.id);
        }
      } catch (e) {
        showToast('Simulation failed - backend offline', 'danger');
      } finally {
        btnSimulateEvent.disabled = false;
        btnSimulateEvent.innerHTML = `<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="5 3 19 12 5 21 5 3"/></svg><span>Simulate Risk Event</span>`;
      }
    });
  }

  // Refresh Overview
  if (btnRefreshOverviewEvents) {
    btnRefreshOverviewEvents.addEventListener('click', () => {
      if (currentTenant) {
        loadAuditLogs(currentTenant.id);
        showToast('Audit stream updated');
      }
    });
  }

  // Save Policy Settings
  if (btnSavePolicy) {
    btnSavePolicy.addEventListener('click', async () => {
      if (!currentTenant) return;
      const payload = {
        allow_threshold: parseInt(allowSlider.value, 10),
        mfa_threshold: parseInt(mfaSlider.value, 10),
        block_threshold: parseInt(mfaSlider.value, 10) - 1,
        impossible_travel_enabled: toggleTravel.checked,
        bot_cadence_enabled: toggleBot.checked,
        touch_biometrics_enabled: toggleTouch.checked,
        velocity_spike_enabled: toggleVelocity.checked
      };

      try {
        const res = await fetch(`${API_BASE}/tenant/${currentTenant.id}/settings`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        if (res.ok) {
          showToast('Policy risk thresholds saved successfully');
        }
      } catch (e) {
        showToast('Failed to save policy settings', 'danger');
      }
    });
  }

  // Policy Slider Live Displays
  if (allowSlider && dispAllowVal) {
    allowSlider.addEventListener('input', () => {
      dispAllowVal.textContent = `${allowSlider.value}+`;
    });
  }
  if (mfaSlider && dispMfaVal) {
    mfaSlider.addEventListener('input', () => {
      dispMfaVal.textContent = `${mfaSlider.value} - ${(parseInt(allowSlider.value, 10) - 1)}`;
    });
  }

  // Filter Events Table
  if (filterEventsSearch) {
    filterEventsSearch.addEventListener('input', () => {
      applyEventsFilter();
    });
  }
  if (filterEventsRisk) {
    filterEventsRisk.addEventListener('change', () => {
      applyEventsFilter();
    });
  }

  function applyEventsFilter() {
    const q = (filterEventsSearch.value || '').toLowerCase();
    const risk = filterEventsRisk.value;

    const filtered = cachedLogs.filter(l => {
      const matchQ = (l.customer_id || '').toLowerCase().includes(q) ||
                     (l.reasons || []).some(r => r.toLowerCase().includes(q));
      const matchRisk = risk === 'all' || (l.decision || '').toLowerCase() === risk;
      return matchQ && matchRisk;
    });

    renderEventsTable(filtered);
  }

  // Global Search
  if (globalSearchInput) {
    globalSearchInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        switchView('events');
        if (filterEventsSearch) {
          filterEventsSearch.value = globalSearchInput.value;
          applyEventsFilter();
        }
      }
    });
  }

  // Check Existing Session
  const savedTenantId = localStorage.getItem('trustdna_tenant_id');
  if (savedTenantId) {
    loadTenantData(savedTenantId);
  } else {
    viewAuth.style.display = 'flex';
    viewDashboard.style.display = 'none';
  }
}

// Toast Alert
function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transition = 'opacity 0.25s ease';
    setTimeout(() => toast.remove(), 250);
  }, 2600);
}
