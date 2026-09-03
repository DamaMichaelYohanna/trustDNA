/**
 * TrustDNA Enterprise Landing Page & Interactive Risk Laboratory
 */

const API_BASE = 'http://localhost:8000/api/v1';

document.addEventListener('DOMContentLoaded', () => {
  initLandingSimulator();
  initDeveloperCodeTabs();
});

/* --------------------------------------------------------------------------
   1. Interactive Risk Laboratory Engine
   -------------------------------------------------------------------------- */
function initLandingSimulator() {
  const deviceSelect = document.getElementById('device-select');
  const networkSelect = document.getElementById('network-select');
  const travelSlider = document.getElementById('travel-slider');
  const travelVal = document.getElementById('travel-val');
  const behaviorSelect = document.getElementById('behavior-select');
  const txAmount = document.getElementById('tx-amount');

  const scoreDisplay = document.getElementById('score-display');
  const decisionBadge = document.getElementById('decision-badge');
  const reasonsContainer = document.getElementById('reasons-container');
  const jsonOutput = document.getElementById('json-output');
  const simLiveStatus = document.getElementById('sim-live-status');

  const barDevice = document.getElementById('bar-device');
  const valDevice = document.getElementById('val-device');
  const barNetwork = document.getElementById('bar-network');
  const valNetwork = document.getElementById('val-network');
  const barTravel = document.getElementById('bar-travel');
  const valTravel = document.getElementById('val-travel');
  const barBehavior = document.getElementById('bar-behavior');
  const valBehavior = document.getElementById('val-behavior');

  const presetButtons = document.querySelectorAll('.btn-preset');

  if (!deviceSelect || !scoreDisplay) return;

  // Preset Handlers
  presetButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      presetButtons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      const p = btn.getAttribute('data-preset');
      if (p === 'legit') {
        deviceSelect.value = 'trusted_mobile';
        networkSelect.value = 'residential';
        travelSlider.value = 25;
        behaviorSelect.value = 'natural';
        txAmount.value = 150;
      } else if (p === 'suspicious') {
        deviceSelect.value = 'new_device';
        networkSelect.value = 'commercial_vpn';
        travelSlider.value = 650;
        behaviorSelect.value = 'slight_anomaly';
        txAmount.value = 3200;
      } else if (p === 'attack') {
        deviceSelect.value = 'emulated';
        networkSelect.value = 'tor_exit';
        travelSlider.value = 2800;
        behaviorSelect.value = 'scripted_bot';
        txAmount.value = 14500;
      }
      runSimulation();
    });
  });

  // Input Change Handlers
  [deviceSelect, networkSelect, behaviorSelect].forEach(el => {
    if (el) el.addEventListener('change', () => {
      presetButtons.forEach(b => b.classList.remove('active'));
      runSimulation();
    });
  });

  if (travelSlider) {
    travelSlider.addEventListener('input', () => {
      presetButtons.forEach(b => b.classList.remove('active'));
      if (travelVal) travelVal.textContent = `${Number(travelSlider.value).toLocaleString()} km/h`;
      runSimulation();
    });
  }

  if (txAmount) {
    txAmount.addEventListener('input', () => {
      presetButtons.forEach(b => b.classList.remove('active'));
      runSimulation();
    });
  }

  async function runSimulation() {
    const dev = deviceSelect.value;
    const net = networkSelect.value;
    const travel = parseInt(travelSlider.value, 10);
    const beh = behaviorSelect.value;
    const amt = parseFloat(txAmount.value) || 100;

    if (travelVal) travelVal.textContent = `${travel.toLocaleString()} km/h`;

    const payload = {
      customer_id: 'usr_82931',
      device: {
        profile: dev === 'trusted_mobile' || dev === 'trusted_desktop' ? 'known_trusted' : dev === 'new_device' ? 'new_fingerprint' : 'emulated_rooted',
        is_headless: dev === 'emulated'
      },
      network: {
        type: net === 'residential' || net === 'cellular' ? 'residential' : net === 'commercial_vpn' ? 'datacenter_vpn' : 'tor_exit'
      },
      travel: {
        distance_km: travel > 1000 ? travel : 25
      },
      behavior: {
        typing_profile: beh === 'natural' ? 'natural' : beh === 'slight_anomaly' ? 'deviated' : 'robotic_paste'
      },
      transaction: {
        amount: amt,
        currency: 'USD'
      }
    };

    try {
      const startT = performance.now();
      const res = await fetch(`${API_BASE}/risk/evaluate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        const data = await res.json();
        const endT = performance.now();
        renderDecision(data, Math.round(endT - startT));
        if (simLiveStatus) {
          simLiveStatus.textContent = `Live Python API (${data.latency_ms || 0.38}ms)`;
          simLiveStatus.className = 'badge badge-low';
        }
        return;
      }
    } catch (e) {
      // Offline fallback heuristic
    }

    // Client Heuristic Fallback
    renderFallback(dev, net, travel, beh, amt);
  }

  function renderDecision(data, clientLat) {
    const score = data.trust_score || 80;
    const dec = (data.decision || 'allow').toUpperCase();
    const sub = data.subscores || {
      device_health: 95,
      network_reputation: 90,
      travel_velocity: 99,
      behavioral_biometrics: 92
    };

    if (scoreDisplay) scoreDisplay.textContent = score;

    if (decisionBadge) {
      decisionBadge.textContent = dec;
      decisionBadge.className = `badge ${dec === 'ALLOW' ? 'badge-low' : dec === 'CHALLENGE' ? 'badge-med' : 'badge-high'}`;
    }

    // Subscores
    if (barDevice) barDevice.style.width = `${sub.device_health}%`;
    if (valDevice) valDevice.textContent = `${Math.round(sub.device_health)}%`;

    if (barNetwork) barNetwork.style.width = `${sub.network_reputation}%`;
    if (valNetwork) valNetwork.textContent = `${Math.round(sub.network_reputation)}%`;

    if (barTravel) barTravel.style.width = `${sub.travel_velocity}%`;
    if (valTravel) valTravel.textContent = `${Math.round(sub.travel_velocity)}%`;

    if (barBehavior) barBehavior.style.width = `${sub.behavioral_biometrics}%`;
    if (valBehavior) valBehavior.textContent = `${Math.round(sub.behavioral_biometrics)}%`;

    // Reasons
    if (reasonsContainer) {
      reasonsContainer.innerHTML = '';
      const rList = data.reasons && data.reasons.length > 0 ? data.reasons : ['Verified Baseline Parameters'];
      rList.forEach(r => {
        const span = document.createElement('span');
        span.className = `badge ${dec === 'ALLOW' ? 'badge-low' : dec === 'CHALLENGE' ? 'badge-med' : 'badge-high'}`;
        span.textContent = r;
        reasonsContainer.appendChild(span);
      });
    }

    // JSON code
    if (jsonOutput) {
      jsonOutput.innerHTML = `<code>${JSON.stringify({
  trust_score: score,
  decision: data.decision,
  latency_ms: data.latency_ms || 0.38,
  reasons: data.reasons || []
}, null, 2)}</code>`;
    }
  }

  function renderFallback(dev, net, travel, beh, amt) {
    let score = 94;
    let reasons = ['Verified Device Baseline', 'Residential Network ISP'];

    if (dev === 'new_device') {
      score -= 20;
      reasons = ['New Device Fingerprint', 'Normal Flight Time Cadence'];
    } else if (dev === 'emulated') {
      score -= 50;
      reasons = ['Headless Chrome Automation Detected', 'Zero Hardware Entropy'];
    }

    if (net === 'commercial_vpn') {
      score -= 15;
      reasons.push('Commercial Datacenter VPN');
    } else if (net === 'tor_exit') {
      score -= 40;
      reasons.push('Tor Anonymizing Exit Node');
    }

    if (travel > 1500) {
      score -= 35;
      reasons.push(`Impossible Travel Delta (${travel} km/h)`);
    }

    if (beh === 'scripted_bot') {
      score -= 40;
      reasons.push('Sub-1ms Keystroke Interval (Bot Injection)');
    }

    score = Math.max(8, Math.min(99, score));
    const dec = score >= 70 ? 'allow' : score >= 40 ? 'challenge' : 'block';

    renderDecision({
      trust_score: score,
      decision: dec,
      reasons: reasons,
      subscores: {
        device_health: dev === 'emulated' ? 15 : dev === 'new_device' ? 65 : 98,
        network_reputation: net === 'tor_exit' ? 10 : net === 'commercial_vpn' ? 55 : 95,
        travel_velocity: travel > 1500 ? 20 : 99,
        behavioral_biometrics: beh === 'scripted_bot' ? 10 : 92
      }
    }, 12);
  }

  // Initial Run
  runSimulation();
}

/* --------------------------------------------------------------------------
   2. Developer Code Tabs Switcher
   -------------------------------------------------------------------------- */
function initDeveloperCodeTabs() {
  const tabs = document.querySelectorAll('.code-tab');
  const panes = document.querySelectorAll('.code-tab-pane');

  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      panes.forEach(p => p.style.display = 'none');

      tab.classList.add('active');
      const targetId = `tab-content-${tab.getAttribute('data-tab')}`;
      const targetPane = document.getElementById(targetId);
      if (targetPane) {
        targetPane.style.display = 'block';
      }
    });
  });
}
