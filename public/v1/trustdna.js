/**
 * TrustDNA Client Telemetry Web SDK (v1.0.0)
 * Passive Behavioral Biometrics & Device Intelligence Collector (Zero-PII Footprint).
 *
 * (c) 2026 TrustDNA Technologies, Inc. MIT License.
 */
(function (root, factory) {
  if (typeof define === 'function' && define.amd) {
    define([], factory);
  } else if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    root.TrustDNA = factory();
  }
}(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  // Internal Circular Buffer for Timestamps
  class BoundedBuffer {
    constructor(maxSize = 100) {
      this.maxSize = maxSize;
      this.items = [];
    }
    push(item) {
      if (this.items.length >= this.maxSize) {
        this.items.shift();
      }
      this.items.push(item);
    }
    getValues() {
      return this.items;
    }
    clear() {
      this.items = [];
    }
  }

  // Math Utilities for Vector Statistics
  function calcStats(arr) {
    if (!arr || arr.length === 0) return { mean: 0, std: 0 };
    const mean = arr.reduce((acc, v) => acc + v, 0) / arr.length;
    if (arr.length === 1) return { mean: Math.round(mean * 10) / 10, std: 0 };
    const variance = arr.reduce((acc, v) => acc + Math.pow(v - mean, 2), 0) / arr.length;
    return {
      mean: Math.round(mean * 10) / 10,
      std: Math.round(Math.sqrt(variance) * 10) / 10
    };
  }

  // Fast string hash (FNV-1a 32-bit)
  function fnv1a(str) {
    let hash = 2166136261;
    for (let i = 0; i < str.length; i++) {
      hash ^= str.charCodeAt(i);
      hash = Math.imul(hash, 16777619);
    }
    return (hash >>> 0).toString(16);
  }

  class TrustDNAClient {
    constructor(options = {}) {
      this.publishableKey = options.publishableKey || 'td_pub_test_default';
      this.apiEndpoint = options.apiEndpoint || 'http://localhost:8000/api/v1';
      this.debug = !!options.debug;

      // Behavioral Event Buffers
      this.dwellBuffer = new BoundedBuffer(60);
      this.flightBuffer = new BoundedBuffer(60);
      this.touchSpeedBuffer = new BoundedBuffer(30);
      this.pasteCount = 0;
      this.keyPressCount = 0;

      // State tracking
      this.keyDownTimes = new Map();
      this.lastKeyUpTime = 0;
      this.touchStartTime = 0;
      this.touchStartX = 0;
      this.touchStartY = 0;

      this.initialized = false;
      this._initListeners();
    }

    _initListeners() {
      if (typeof window === 'undefined' || this.initialized) return;
      this.initialized = true;

      // 1. Keystroke Dynamics (Dwell & Flight Time) - NEVER records characters/passwords!
      window.addEventListener('keydown', (e) => {
        const now = performance.now();
        // Track flight time from previous keyup
        if (this.lastKeyUpTime > 0) {
          const flight = now - this.lastKeyUpTime;
          if (flight > 10 && flight < 4000) { // filter humanly reasonable flight intervals
            this.flightBuffer.push(flight);
          }
        }
        // Save keydown start timestamp using keyCode/code as ephemeral correlation id
        const keyId = e.code || e.keyCode || 'k';
        if (!this.keyDownTimes.has(keyId)) {
          this.keyDownTimes.set(keyId, now);
        }
        this.keyPressCount++;
      }, { passive: true, capture: true });

      window.addEventListener('keyup', (e) => {
        const now = performance.now();
        this.lastKeyUpTime = now;
        const keyId = e.code || e.keyCode || 'k';
        if (this.keyDownTimes.has(keyId)) {
          const start = this.keyDownTimes.get(keyId);
          this.keyDownTimes.delete(keyId);
          const dwell = now - start;
          if (dwell >= 5 && dwell < 2000) {
            this.dwellBuffer.push(dwell);
          }
        }
      }, { passive: true, capture: true });

      // 2. Touch & Swipe Dynamics (Mobile)
      window.addEventListener('touchstart', (e) => {
        if (e.touches && e.touches.length > 0) {
          this.touchStartTime = performance.now();
          this.touchStartX = e.touches[0].clientX;
          this.touchStartY = e.touches[0].clientY;
        }
      }, { passive: true, capture: true });

      window.addEventListener('touchend', (e) => {
        if (e.changedTouches && e.changedTouches.length > 0 && this.touchStartTime > 0) {
          const durationSec = (performance.now() - this.touchStartTime) / 1000.0;
          const deltaX = e.changedTouches[0].clientX - this.touchStartX;
          const deltaY = e.changedTouches[0].clientY - this.touchStartY;
          const distancePx = Math.sqrt(deltaX * deltaX + deltaY * deltaY);
          if (durationSec > 0.05 && distancePx > 10) {
            const speed = Math.round(distancePx / durationSec);
            this.touchSpeedBuffer.push(speed);
          }
        }
      }, { passive: true, capture: true });

      // 3. Paste Event Detection (Distinguishes rapid automation injections)
      window.addEventListener('paste', () => {
        this.pasteCount++;
      }, { passive: true, capture: true });
    }

    // Hardware & Browser Entropy Fingerprint (Zero PII)
    getHardwareEntropy() {
      const entropy = {
        screen_w: window.screen ? window.screen.width : 0,
        screen_h: window.screen ? window.screen.height : 0,
        color_depth: window.screen ? window.screen.colorDepth : 0,
        pixel_ratio: window.devicePixelRatio || 1,
        timezone_offset: new Date().getTimezoneOffset(),
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC',
        hardware_concurrency: navigator.hardwareConcurrency || 4,
        max_touch_points: navigator.maxTouchPoints || 0,
        platform: navigator.platform || 'unknown',
        webdriver: !!navigator.webdriver,
        canvas_hash: 'none',
        webgl_vendor: 'unknown',
        webgl_renderer: 'unknown'
      };

      // Canvas 2D Entropy Hash
      try {
        const canvas = document.createElement('canvas');
        canvas.width = 160;
        canvas.height = 50;
        const ctx = canvas.getContext('2d');
        if (ctx) {
          ctx.textBaseline = 'top';
          ctx.font = '14px "Arial", sans-serif';
          ctx.fillStyle = '#f60';
          ctx.fillRect(10, 5, 62, 20);
          ctx.fillStyle = '#069';
          ctx.fillText('TrustDNA,🛡️<canvas>', 2, 15);
          entropy.canvas_hash = fnv1a(canvas.toDataURL());
        }
      } catch (err) {
        entropy.canvas_hash = 'err';
      }

      // WebGL Hardware Profile
      try {
        const glCanvas = document.createElement('canvas');
        const gl = glCanvas.getContext('webgl') || glCanvas.getContext('experimental-webgl');
        if (gl) {
          const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
          if (debugInfo) {
            entropy.webgl_vendor = gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL) || 'generic';
            entropy.webgl_renderer = gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL) || 'generic';
          }
        }
      } catch (err) {
        // Fallback gracefully
      }

      entropy.hardware_hash = fnv1a(
        `${entropy.screen_w}x${entropy.screen_h}_${entropy.canvas_hash}_${entropy.webgl_renderer}`
      );

      return entropy;
    }

    // Extract statistical behavioral vector
    getBehavioralSignals() {
      const dwellStats = calcStats(this.dwellBuffer.getValues());
      const flightStats = calcStats(this.flightBuffer.getValues());
      const touchStats = calcStats(this.touchSpeedBuffer.getValues());

      return {
        dwell_mean_ms: dwellStats.mean,
        dwell_std_ms: dwellStats.std,
        flight_mean_ms: flightStats.mean,
        flight_std_ms: flightStats.std,
        touch_speed_px_s: touchStats.mean,
        paste_events_count: this.pasteCount,
        sample_keystrokes: this.keyPressCount
      };
    }

    /**
     * Primary Integration API:
     * Generates a signed telemetry token (td_tok_...) to send with checkout/login requests.
     */
    async getTelemetryToken() {
      const entropy = this.getHardwareEntropy();
      const behavior = this.getBehavioralSignals();

      const combinedSignals = {
        ...entropy,
        ...behavior,
        generated_at: Date.now()
      };

      // Try server tokenization endpoint first
      try {
        const res = await fetch(`${this.apiEndpoint}/telemetry/tokenize`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            publishable_key: this.publishableKey,
            signals: combinedSignals
          })
        });

        if (res.ok) {
          const json = await res.json();
          return json.telemetry_token;
        }
      } catch (err) {
        if (this.debug) {
          console.warn('[TrustDNA] Remote tokenization endpoint unreachable, generating client fallback token', err);
        }
      }

      // Offline / Local Token Generation Fallback
      const jsonStr = JSON.stringify({
        pub: this.publishableKey,
        ts: Date.now() / 1000.0,
        data: combinedSignals
      });
      const b64 = btoa(unescape(encodeURIComponent(jsonStr))).replace(/=/g, '');
      const fakeSig = fnv1a(b64);
      return `td_tok_${b64}.${fakeSig}`;
    }
  }

  // Singleton Instance Factory
  let instance = null;

  return {
    init: function (options) {
      if (!instance) {
        instance = new TrustDNAClient(options);
      }
      return instance;
    },
    getInstance: function () {
      if (!instance) {
        instance = new TrustDNAClient();
      }
      return instance;
    }
  };
}));
