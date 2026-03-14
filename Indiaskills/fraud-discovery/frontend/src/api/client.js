import axios from 'axios';

// Use Render backend for production
const API_BASE = 'https://fraud-discovery-api.onrender.com/api';

const apiClient = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const transactionsAPI = {
  getTransactions: (page = 1, limit = 50, riskTier = null) =>
    apiClient.get('/transactions', {
      params: { page, limit, risk_tier: riskTier }
    }),

  getTransaction: (id) =>
    apiClient.get(`/transactions/${id}`),

  deleteAllTransactions: () =>
    apiClient.delete('/transactions'),

  bulkUpload: (transactions) =>
    apiClient.post('/transactions/bulk-upload', transactions),
};

export const analysisAPI = {
  generateData: (size = 10000) =>
    apiClient.post('/generate', { size }),

  runAnalysis: () =>
    apiClient.post('/analyze'),
};

export const dashboardAPI = {
  getStats: () =>
    apiClient.get('/dashboard/stats'),

  getRiskBreakdown: () =>
    apiClient.get('/dashboard/risk-breakdown'),

  getAlerts: (limit = 50) =>
    apiClient.get('/alerts', { params: { limit } }),

  getPatterns: () =>
    apiClient.get('/patterns'),

  getChains: () =>
    apiClient.get('/chains'),

  healthCheck: () =>
    apiClient.get('/health'),
};

export default apiClient;
