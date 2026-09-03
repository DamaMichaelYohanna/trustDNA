# Implementation Plan: Third-Party External Integration Layer

Build the complete 2-legged third-party integration system for TrustDNA:
1. Client-Side Telemetry Collector (`trustdna.js`) capturing passive typing cadence, touch dynamics, and hardware entropy with zero-PII footprint.
2. Backend Telemetry Tokenization & Dual Key Authentication (Publishable vs. Secret Keys).
3. Machine Learning Feature Pipeline collecting anonymous training vectors for future AI models.
4. Interactive Third-Party Checkout Demonstration showing real-world integration in action.

---

## User Review Required

> [!IMPORTANT]
> - **Zero-PII Privacy Protection**: The client-side JavaScript collector will never capture pressed characters, field text, or passwords. It strictly records delta intervals (flight times, dwell times in milliseconds) and movement geometry (swipe curvatures, velocity).
> - **Dual Key Model**:
>   - `td_pub_test_...` / `td_pub_live_...`: Publishable keys embedded on client websites, restricted to telemetry collection and token generation.
>   - `td_sec_test_...` / `td_sec_live_...`: Secret keys kept strictly on customer backends to request risk decisions.
> - **Performance**: The SDK script will be standalone vanilla JavaScript (< 12KB unminified, zero external dependencies) with passive event listeners (`{ passive: true }`) ensuring zero impact on host website frame rate.

---

## Proposed Changes

### 1. Client-Side Telemetry Collector (`public/v1/trustdna.js`)

#### [NEW] [trustdna.js](file:///c:/Users/Dama-PC/Documents/Python%20Projects/trustDNA/public/v1/trustdna.js)
- Standalone UMD/browser script exposing `window.TrustDNA`.
- **Hardware Entropy Gatherer**:
  - Canvas 2D rendering hash & WebGL vendor/renderer strings.
  - Screen dimensions, color depth, timezone offset, hardware concurrency.
  - Headless browser signals (missing plugins, webdriver flag, anomalous user agent).
- **Behavioral Biometrics Recorder**:
  - Global passive listeners for `keydown` / `keyup` calculating dwell times and flight times.
  - Touch listeners (`touchstart`, `touchmove`, `touchend`) calculating swipe curvature, contact duration, and touch force.
  - Paste event listener detecting instant clipboard injections.
- **Token Generator**:
  - `trustdna.getTelemetryToken()`: Packages and compresses the mathematical feature vector into an encrypted/signed token string (`td_tok_...`).

---

### 2. Backend Tokenization & Dual Key Authentication (`backend/app/`)

#### [NEW] [backend/app/engine/tokens.py](file:///c:/Users/Dama-PC/Documents/Python%20Projects/trustDNA/backend/app/engine/tokens.py)
- Cryptographic token generation and decoding using URL-safe base64 / HMAC signing.
- Decodes client `td_tok_...` into structured telemetry models for the scoring engine.

#### [NEW] [backend/app/engine/training.py](file:///c:/Users/Dama-PC/Documents/Python%20Projects/trustDNA/backend/app/engine/training.py)
- Feature vector extraction and buffer for ML training data.
- Records: `dwell_mean_ms`, `flight_std_ms`, `touch_speed_px_s`, `paste_count`, `hardware_hash`, `target_decision`.
- Exposes administrative endpoint to export training datasets in CSV or JSON format.

#### [MODIFY] [backend/app/api/routes.py](file:///c:/Users/Dama-PC/Documents/Python%20Projects/trustDNA/backend/app/api/routes.py)
- Add endpoints:
  - `POST /api/v1/telemetry/token`: Generates a verified telemetry token using a Publishable Key (`td_pub_...`).
  - `POST /api/v1/risk/evaluate`: Enhanced to accept either a raw telemetry payload OR a `telemetry_token` directly from client forms.
  - `GET /api/v1/ml/dataset`: Exports collected anonymous feature vectors for training AI models.

---

### 3. Interactive Integration Showcase (`demo/checkout.html`)

#### [NEW] [demo/checkout.html](file:///c:/Users/Dama-PC/Documents/Python%20Projects/trustDNA/demo/checkout.html)
- A realistic third-party e-commerce checkout page ("Acme Electronics Store").
- Shows a 3-line `<script src="/v1/trustdna.js">` integration.
- Demonstrates:
  1. User types in payment fields (passive telemetry tracking).
  2. Submits order -> generates `td_tok_...`.
  3. Third-party backend evaluates risk -> allows, challenges with OTP, or blocks.
  4. Live inspectable telemetry payload drawer so developers can see what was captured.

---

## Verification Plan

### Automated Tests
1. Add test suite in `backend/tests/test_tokens_and_sdk.py`:
   - Verify token encoding and decoding integrity.
   - Verify publishable vs secret key validation.
   - Verify risk evaluation via `telemetry_token`.
   - Verify training feature dataset export.
2. Run pytest:
   ```bash
   python -m pytest tests/ -v
   ```

### Manual Verification
1. Open the integration demo at `http://localhost:5173/demo/checkout.html`.
2. Type naturally into the checkout form and submit: confirm `ALLOW` decision.
3. Paste text rapidly or simulate bot input: confirm `CHALLENGE` or `BLOCK` decision.
4. Check `GET /api/v1/ml/dataset` to confirm training features were recorded cleanly.
