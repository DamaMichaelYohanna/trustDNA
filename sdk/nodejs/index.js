/**
 * TrustDNA Node.js SDK
 * Enterprise Fraud Prevention & Risk Decision Engine
 */

class TrustDNA {
  /**
   * @param {Object} options
   * @param {string} options.secretKey - Your organization's secret key (td_sec_...)
   * @param {string} [options.baseUrl] - TrustDNA API base URL
   * @param {number} [options.timeout] - Request timeout in milliseconds
   */
  constructor({ secretKey, baseUrl = 'http://localhost:8000/api/v1', timeout = 3000 } = {}) {
    if (!secretKey) {
      throw new Error('TrustDNA: secretKey is required (e.g. td_sec_...)');
    }
    this.secretKey = secretKey;
    this.baseUrl = baseUrl.replace(/\/$/, '');
    this.timeout = timeout;

    this.risk = {
      /**
       * Evaluates transaction risk synchronously in < 1ms
       * @param {Object} params
       * @param {string} params.customerId - End user ID
       * @param {string} [params.telemetryToken] - Token from trustdna.js
       * @param {number} [params.amount] - Transaction amount
       * @param {string} [params.currency] - Currency (default 'USD')
       * @param {Object} [params.customSignals] - Additional arbitrary signals
       */
      evaluate: async (params) => {
        const payload = {
          customer_id: params.customerId || params.customer_id,
          telemetry_token: params.telemetryToken || params.telemetry_token,
          transaction: {
            amount: params.amount || 0,
            currency: params.currency || 'USD',
            is_first_time_user: false,
            custom_signals: params.customSignals || params.custom_signals
          }
        };

        const res = await fetch(`${this.baseUrl}/risk/evaluate`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${this.secretKey}`,
            'User-Agent': '@trustdna/node v1.0.0'
          },
          body: JSON.stringify(payload)
        });

        if (res.status === 401) {
          throw new Error('TrustDNA Authentication Error: Invalid or revoked secret key.');
        }

        if (!res.ok) {
          const errText = await res.text();
          throw new Error(`TrustDNA API Error (${res.status}): ${errText}`);
        }

        return await res.json();
      }
    };
  }
}

module.exports = TrustDNA;
module.exports.TrustDNA = TrustDNA;
module.exports.default = TrustDNA;
