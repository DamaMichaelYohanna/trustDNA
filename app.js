/* ==========================================================================
   TrustDNA - Interactive Engine & App Logic
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
  initSimulator();
  initCodeTabs();
  initPricingCalculator();
  initSandboxModal();
  initCopyButtons();
});

/* --------------------------------------------------------------------------
   1. Live Risk Simulator Engine
   -------------------------------------------------------------------------- */
function initSimulator() {
  const deviceSelect = document.getElementById('device-select');
  const networkSelect = document.getElementById('network-select');
  const travelSlider = document.getElementById('travel-slider');
  const travelVal = document.getElementById('travel-val');
  const behaviorSelect = document.getElementById('behavior-select');
  const amountSlider = document.getElementById('amount-slider');
  const amountVal = document.getElementById('amount-val');

  const riskScoreEl = document.getElementById('risk-score');
  const scoreCircle = document.getElementById('score-circle');
  const decisionBadge = document.getElementById('decision-badge');
  const decisionText = document.getElementById('decision-text');
  const riskLevelEl = document.getElementById('risk-level');
  const reasonsList = document.getElementById('reasons-list');
  const jsonCodeDisplay = document.getElementById('json-code-display');
  const evalTimeEl = document.getElementById('eval-time');

  const subDeviceBar = document.getElementById('sub-device-bar');
  const subDeviceVal = document.getElementById('sub-device-val');
  const subBehaviorBar = document.getElementById('sub-behavior-bar');
  const subBehaviorVal = document.getElementById('sub-behavior-val');
  const subNetworkBar = document.getElementById('sub-network-bar');
  const subNetworkVal = document.getElementById('sub-network-val');
  const subTxBar = document.getElementById('sub-tx-bar');
  const subTxVal = document.getElementById('sub-tx-val');

  const presetButtons = document.querySelectorAll('.preset-btn');
  const resetBtn = document.getElementById('reset-sim-btn');

  // Format currency
  const formatCurrency = (val) => {
    return '₦' + Number(val).toLocaleString('en-NG');
  };

  // Recalculate Risk Decision
  function calculateRisk() {
    const device = deviceSelect.value;
    const network = networkSelect.value;
    const travelKm = parseInt(travelSlider.value, 10);
    const behavior = behaviorSelect.value;
    const amount = parseInt(amountSlider.value, 10);

    // Update label displays
    travelVal.textContent = travelKm > 800 ? `${travelKm.toLocaleString()} km (Impossible Travel!)` : `${travelKm.toLocaleString()} km (Normal)`;
    amountVal.textContent = formatCurrency(amount);

    let deviceScore = 95;
    let networkScore = 92;
    let behaviorScore = 90;
    let txScore = 90;
    const reasons = [];

    // Device Factor
    if (device === 'known_trusted') {
      deviceScore = 96;
      reasons.push({ text: 'known_device_profile', type: 'success' });
    } else if (device === 'new_fingerprint') {
      deviceScore = 60;
      reasons.push({ text: 'new_device_fingerprint', type: 'warning' });
    } else if (device === 'emulated_rooted') {
      deviceScore = 15;
      reasons.push({ text: 'emulated_or_rooted_environment', type: 'danger' });
    }

    // Network Factor
    if (network === 'residential') {
      networkScore = 94;
      reasons.push({ text: 'residential_ip_clean', type: 'success' });
    } else if (network === 'datacenter_vpn') {
      networkScore = 40;
      reasons.push({ text: 'commercial_vpn_or_datacenter_proxy', type: 'warning' });
    } else if (network === 'tor_exit') {
      networkScore = 8;
      reasons.push({ text: 'tor_anonymizing_exit_node', type: 'danger' });
    }

    // Travel Factor
    if (travelKm > 800) {
      networkScore = Math.min(networkScore, 20);
      reasons.push({ text: `impossible_travel_delta_${travelKm}km`, type: 'danger' });
    }

    // Behavior Factor
    if (behavior === 'natural') {
      behaviorScore = 92;
      reasons.push({ text: 'consistent_typing_cadence', type: 'success' });
    } else if (behavior === 'deviated') {
      behaviorScore = 55;
      reasons.push({ text: 'behavioral_flight_time_variance', type: 'warning' });
    } else if (behavior === 'robotic_paste') {
      behaviorScore = 12;
      reasons.push({ text: 'bot_automated_keystroke_cadence', type: 'danger' });
    }

    // Transaction Factor
    if (amount <= 100000) {
      txScore = 95;
      reasons.push({ text: 'within_normal_spending_baseline', type: 'success' });
    } else if (amount <= 1000000) {
      txScore = 65;
      reasons.push({ text: 'moderate_spend_deviation', type: 'warning' });
    } else {
      txScore = 25;
      reasons.push({ text: 'high_value_transaction_spike', type: 'danger' });
    }

    // Composite Weighted Calculation
    // Device: 30%, Network: 25%, Behavior: 25%, Transaction: 20%
    let compositeScore = Math.round(
      (deviceScore * 0.30) +
      (networkScore * 0.25) +
      (behaviorScore * 0.25) +
      (txScore * 0.20)
    );

    // Hard Override Rules
    if (network === 'tor_exit' || (device === 'emulated_rooted' && amount > 500000) || travelKm > 2000) {
      compositeScore = Math.min(compositeScore, 22);
    }

    // Clamp score 0 - 100
    compositeScore = Math.max(5, Math.min(99, compositeScore));

    // Decision Logic
    let decision = 'allow';
    let riskLevel = 'LOW RISK';
    let decisionClass = 'badge-allow';
    let icon = '✓';
    let strokeColor = 'var(--emerald)';
    let levelClass = 'text-emerald';

    if (compositeScore >= 75) {
      decision = 'allow';
      riskLevel = 'LOW RISK';
      decisionClass = 'badge-allow';
      icon = '✓';
      strokeColor = 'var(--emerald)';
      levelClass = 'text-emerald';
    } else if (compositeScore >= 40) {
      decision = 'challenge';
      riskLevel = 'MEDIUM RISK (STEP-UP MFA)';
      decisionClass = 'badge-challenge';
      icon = '⚠';
      strokeColor = 'var(--amber)';
      levelClass = 'text-amber';
    } else {
      decision = 'block';
      riskLevel = 'HIGH RISK (SECURITY BLOCKED)';
      decisionClass = 'badge-block';
      icon = '✕';
      strokeColor = 'var(--red)';
      levelClass = 'text-red';
    }

    // Update DOM UI
    riskScoreEl.textContent = compositeScore;
    scoreCircle.style.background = `conic-gradient(${strokeColor} ${compositeScore}%, rgba(255, 255, 255, 0.08) 0)`;
    scoreCircle.style.boxShadow = `0 0 24px ${strokeColor}40`;

    decisionBadge.className = `decision-badge ${decisionClass}`;
    decisionBadge.innerHTML = `<span class="decision-icon">${icon}</span> <span>${decision.toUpperCase()}</span>`;
    
    riskLevelEl.className = `risk-level-val ${levelClass}`;
    riskLevelEl.textContent = riskLevel;

    // Sub-scores
    subDeviceBar.style.width = `${deviceScore}%`;
    subDeviceVal.textContent = deviceScore;
    subBehaviorBar.style.width = `${behaviorScore}%`;
    subBehaviorVal.textContent = behaviorScore;
    subNetworkBar.style.width = `${networkScore}%`;
    subNetworkVal.textContent = networkScore;
    subTxBar.style.width = `${txScore}%`;
    subTxVal.textContent = txScore;

    // Simulated latency (22ms - 46ms)
    const simulatedLatency = Math.floor(Math.random() * 20) + 24;
    evalTimeEl.textContent = `Evaluated in ${simulatedLatency}ms`;

    // Render Reason Tags
    reasonsList.innerHTML = reasons.map(r => `
      <span class="reason-tag ${r.type}">
        ${r.type === 'success' ? '✓' : r.type === 'warning' ? '⚠' : '✕'} ${r.text}
      </span>
    `).join('');

    // Generate Formatted JSON Payload
    const jsonPayload = {
      trust_score: compositeScore,
      decision: decision,
      risk_level: decision === 'allow' ? 'low' : decision === 'challenge' ? 'medium' : 'high',
      latency_ms: simulatedLatency,
      customer_id: 'usr_82931',
      reasons: reasons.map(r => r.text),
      module_scores: {
        device: deviceScore,
        behavior: behaviorScore,
        network: networkScore,
        transaction: txScore
      },
      recommended_action: decision === 'allow' ? 'proceed' : decision === 'challenge' ? 'require_totp_mfa' : 'block_and_terminate_session'
    };

    jsonCodeDisplay.innerHTML = `<code>${highlightJson(JSON.stringify(jsonPayload, null, 2))}</code>`;
  }

  // Syntax highlight JSON output
  function highlightJson(json) {
    return json.replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, function (match) {
      let cls = 'number';
      if (/^"/.test(match)) {
        if (/:$/.test(match)) {
          cls = 'keyword';
        } else {
          cls = 'string';
        }
      } else if (/true|false/.test(match)) {
        cls = 'type';
      } else if (/null/.test(match)) {
        cls = 'comment';
      }
      return '<span class="' + cls + '">' + match + '</span>';
    });
  }

  // Event Listeners for Simulator
  [deviceSelect, networkSelect, behaviorSelect].forEach(el => el.addEventListener('change', () => {
    uncheckPresets();
    calculateRisk();
  }));

  travelSlider.addEventListener('input', () => {
    uncheckPresets();
    calculateRisk();
  });

  amountSlider.addEventListener('input', () => {
    uncheckPresets();
    calculateRisk();
  });

  function uncheckPresets() {
    presetButtons.forEach(b => b.classList.remove('active'));
  }

  // Presets Handlers
  presetButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      presetButtons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      const preset = btn.getAttribute('data-preset');
      if (preset === 'legit') {
        deviceSelect.value = 'known_trusted';
        networkSelect.value = 'residential';
        travelSlider.value = 0;
        behaviorSelect.value = 'natural';
        amountSlider.value = 45000;
      } else if (preset === 'suspicious') {
        deviceSelect.value = 'new_fingerprint';
        networkSelect.value = 'datacenter_vpn';
        travelSlider.value = 450;
        behaviorSelect.value = 'deviated';
        amountSlider.value = 650000;
      } else if (preset === 'attack') {
        deviceSelect.value = 'emulated_rooted';
        networkSelect.value = 'tor_exit';
        travelSlider.value = 3200;
        behaviorSelect.value = 'robotic_paste';
        amountSlider.value = 4500000;
      }
      calculateRisk();
    });
  });

  // Reset Button
  resetBtn.addEventListener('click', () => {
    presetButtons[0].click();
  });

  // Initial Run
  calculateRisk();
}

/* --------------------------------------------------------------------------
   2. Developer Experience (Code Tabs)
   -------------------------------------------------------------------------- */
function initCodeTabs() {
  const tabs = document.querySelectorAll('.code-tab');
  const panes = document.querySelectorAll('.tab-pane');

  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      panes.forEach(p => p.classList.remove('active'));

      tab.classList.add('active');
      const targetId = `pane-${tab.getAttribute('data-tab')}`;
      const targetPane = document.getElementById(targetId);
      if (targetPane) {
        targetPane.classList.add('active');
      }
    });
  });
}

/* --------------------------------------------------------------------------
   3. Interactive Pricing Volume Calculator
   -------------------------------------------------------------------------- */
function initPricingCalculator() {
  const slider = document.getElementById('pricing-slider');
  const volumeLabel = document.getElementById('calc-volume-label');
  const costLabel = document.getElementById('calc-cost');

  if (!slider || !volumeLabel || !costLabel) return;

  slider.addEventListener('input', () => {
    const volume = parseInt(slider.value, 10);
    volumeLabel.textContent = `${volume.toLocaleString()} risk checks / month`;

    let cost = 0;
    let tierRec = 'Starter';

    if (volume <= 5000) {
      cost = 0;
      tierRec = 'Starter (Free)';
    } else if (volume <= 100000) {
      // Base $49 + volume scale
      cost = Math.round(29 + (volume / 1000) * 0.9);
      tierRec = 'Growth Tier';
    } else {
      cost = Math.round(120 + (volume / 1000) * 0.7);
      tierRec = 'Scale Tier';
    }

    costLabel.textContent = `$${cost} / month (${tierRec})`;
  });
}

/* --------------------------------------------------------------------------
   4. Instant Sandbox Key Generator Modal
   -------------------------------------------------------------------------- */
function initSandboxModal() {
  const modal = document.getElementById('sandbox-modal');
  const openBtns = [
    document.getElementById('open-sandbox-btn'),
    document.getElementById('cta-sandbox-btn')
  ];
  const getStartedBtns = document.querySelectorAll('.get-started-btn');
  const closeBtn = document.getElementById('close-modal-btn');
  const doneBtn = document.getElementById('done-modal-btn');
  const form = document.getElementById('sandbox-gen-form');
  const formView = document.getElementById('modal-form-view');
  const keysView = document.getElementById('modal-keys-view');
  const jumpToDocsBtn = document.getElementById('jump-to-docs-btn');

  const openModal = () => {
    modal.classList.add('open');
    formView.classList.remove('hidden');
    keysView.classList.add('hidden');
  };

  const closeModal = () => {
    modal.classList.remove('open');
  };

  openBtns.forEach(btn => {
    if (btn) btn.addEventListener('click', openModal);
  });

  getStartedBtns.forEach(btn => {
    btn.addEventListener('click', openModal);
  });

  if (closeBtn) closeBtn.addEventListener('click', closeModal);
  if (doneBtn) doneBtn.addEventListener('click', closeModal);
  if (jumpToDocsBtn) {
    jumpToDocsBtn.addEventListener('click', () => {
      closeModal();
    });
  }

  modal.addEventListener('click', (e) => {
    if (e.target === modal) closeModal();
  });

  // Generate Keys Form Submit
  if (form) {
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      
      // Generate random mock sandbox keys
      const randomHex = () => Math.random().toString(16).substring(2, 10);
      const pubKey = `td_pub_test_${randomHex()}${randomHex()}`;
      const secKey = `td_sec_test_${randomHex()}${randomHex()}`;

      document.getElementById('gen-pub-key').value = pubKey;
      document.getElementById('gen-sec-key').value = secKey;

      formView.classList.add('hidden');
      keysView.classList.remove('hidden');
      showToast('🎉 Sandbox keys generated successfully!');
    });
  }

  // Copy buttons in modal
  document.querySelectorAll('.btn-copy-key').forEach(btn => {
    btn.addEventListener('click', () => {
      const targetId = btn.getAttribute('data-target');
      const input = document.getElementById(targetId);
      if (input) {
        navigator.clipboard.writeText(input.value);
        btn.textContent = 'Copied!';
        showToast('Copied key to clipboard');
        setTimeout(() => { btn.textContent = 'Copy'; }, 2000);
      }
    });
  });
}

/* --------------------------------------------------------------------------
   5. Clipboard Copy Utilities & Toast Alerts
   -------------------------------------------------------------------------- */
function initCopyButtons() {
  // Copy JSON Button
  const copyJsonBtn = document.getElementById('copy-json-btn');
  const copyJsonText = document.getElementById('copy-json-text');
  const jsonCodeDisplay = document.getElementById('json-code-display');

  if (copyJsonBtn && jsonCodeDisplay) {
    copyJsonBtn.addEventListener('click', () => {
      const rawText = jsonCodeDisplay.innerText;
      navigator.clipboard.writeText(rawText);
      copyJsonText.textContent = 'Copied!';
      showToast('JSON Response copied to clipboard!');
      setTimeout(() => {
        copyJsonText.textContent = 'Copy JSON';
      }, 2000);
    });
  }

  // Copy Code Snippets
  document.querySelectorAll('.btn-copy-code').forEach(btn => {
    btn.addEventListener('click', () => {
      const parentPane = btn.closest('.tab-pane');
      const codeBlock = parentPane ? parentPane.querySelector('.code-block') : null;
      if (codeBlock) {
        navigator.clipboard.writeText(codeBlock.innerText);
        const span = btn.querySelector('span');
        if (span) span.textContent = 'Copied!';
        showToast('Code snippet copied to clipboard!');
        setTimeout(() => {
          if (span) span.textContent = 'Copy';
        }, 2000);
      }
    });
  });
}

function showToast(message) {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.textContent = message;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transition = 'opacity 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 2500);
}
