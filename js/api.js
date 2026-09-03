/**
 * TrustDNA Frontend API Client Module
 * Handles centralized network requests, headers, error parsing, and session tokens.
 */

export const API_BASE = 'http://localhost:8000/api/v1';

export class TrustDNAApiClient {
  constructor(baseUrl = API_BASE) {
    this.baseUrl = baseUrl;
  }

  getHeaders(customHeaders = {}) {
    const headers = {
      'Content-Type': 'application/json',
      ...customHeaders
    };
    const sessionToken = localStorage.getItem('trustdna_session_token');
    if (sessionToken && !headers['Authorization']) {
      headers['Authorization'] = `Bearer ${sessionToken}`;
    }
    return headers;
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint}`;
    const headers = this.getHeaders(options.headers);
    
    try {
      const response = await fetch(url, {
        ...options,
        headers
      });
      
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        const errorMsg = data.detail || data.message || `HTTP ${response.status}: Request failed`;
        throw new Error(errorMsg);
      }
      return data;
    } catch (err) {
      console.error(`[TrustDNA API Error] ${endpoint}:`, err);
      throw err;
    }
  }

  // Health & Stats
  async getHealth() {
    return this.request('/health');
  }

  // Auth & Tenants
  async registerTenant(payload) {
    return this.request('/auth/register', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  }

  async loginTenant(payload) {
    return this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  }

  async listTenants() {
    return this.request('/auth/tenants');
  }

  // Tenant Account Management
  async getTenantProfile(tenantId) {
    return this.request(`/tenant/${tenantId}/profile`);
  }

  async createApiKey(tenantId, payload) {
    return this.request(`/tenant/${tenantId}/keys`, {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  }

  async revokeApiKey(tenantId, keyId) {
    return this.request(`/tenant/${tenantId}/keys/${keyId}/revoke`, {
      method: 'POST'
    });
  }

  async updateTenantSettings(tenantId, settings) {
    return this.request(`/tenant/${tenantId}/settings`, {
      method: 'PUT',
      body: JSON.stringify(settings)
    });
  }

  async getTenantAuditLogs(tenantId, limit = 50) {
    return this.request(`/tenant/${tenantId}/audit-logs?limit=${limit}`);
  }

  // Risk Scoring
  async evaluateRisk(payload, secretKey = null) {
    const headers = secretKey ? { 'Authorization': `Bearer ${secretKey}` } : {};
    return this.request('/risk/evaluate', {
      method: 'POST',
      headers,
      body: JSON.stringify(payload)
    });
  }

  // Telemetry Tokenization
  async tokenizeSignals(publishableKey, signals) {
    return this.request('/telemetry/tokenize', {
      method: 'POST',
      body: JSON.stringify({
        publishable_key: publishableKey,
        signals
      })
    });
  }
}

export const api = new TrustDNAApiClient();
