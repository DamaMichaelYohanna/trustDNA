# TrustDNA 🛡️
> **The Programmable Trust Layer for Modern Digital Applications**  
> *"Stripe for Risk & Security Decisions"*

TrustDNA is a plug-in risk intelligence infrastructure layer that evaluates whether a user, device, session, or transaction should be trusted in real-time ($< 45\text{ms}$).

---

## ⚡ Key Features

- **Instant Risk Decisions**: Evaluates composite risk and returns actionable outcomes (`ALLOW`, `CHALLENGE (MFA)`, `BLOCK`).
- **Zero-PII Footprint**: Operates on opaque telemetry and hardware features—never asks for user passwords, cleartext names, or bank account balances.
- **Modular Plugin Engine**:
  - 📱 **Device Intelligence**: Hardware entropy, canvas/WebGL hash, emulator & root detection.
  - 🧠 **Behavioral Biometrics**: Continuous passive keystroke flight-time & cadence variance.
  - 💳 **Transaction Risk**: Velocity sliding windows and spending spike anomaly modeling.
  - 🌐 **Network & VPN Shield**: Tor exit node detection, commercial VPNs, and datacenter proxy flags.
  - ✈️ **Impossible Travel**: Geographic velocity ($> 800\text{ km/h}$) concurrent session detection.
  - 🤖 **Bot & Automation Defense**: Headless browser (Puppeteer, Playwright, CDP) detection.
- **Developer-First Integration**: 3-line frontend Web SDK (`@trustdna/web`) and simple REST APIs for Node.js, Python FastAPI, Go, and cURL.
- **Configurable Policy Engine**: Define custom enforcement thresholds without redeploying applications.

---

## 🚀 Quickstart

### 1. Run the Interactive Showcase Locally
```bash
# Clone the repository
git clone https://github.com/DamaMichaelYohanna/trustDNA.git
cd trustDNA

# Start local server
python -m http.server 5173
```
Open **[http://localhost:5173](http://localhost:5173)** in your browser to experience the live simulator!

---

## 💻 30-Second Integration Example

### Frontend (Web SDK)
```html
<script src="https://cdn.trustdna.com/v1/sdk.js"></script>
<script>
  const trustdna = TrustDNA.init({ publishableKey: "td_pub_live_xxxx" });
  const telemetryToken = await trustdna.getTelemetryToken();
  // Send telemetryToken along with your action payload to your backend
</script>
```

### Backend (Node.js)
```javascript
import { TrustDNA } from "@trustdna/node";
const trustdna = new TrustDNA({ secretKey: process.env.TRUSTDNA_SECRET_KEY });

const assessment = await trustdna.risk.evaluate({
  userId: req.user.id,
  telemetryToken: req.body.trustdna_token,
  transaction: { amount: 450000, currency: "NGN" }
});

if (assessment.decision === "challenge") {
  return res.json({ requireMFA: true });
}
```

---

## 📄 License
MIT © 2026 TrustDNA Technologies, Inc.
