import { useState, useEffect } from 'react';
import { analysisAPI, dashboardAPI } from '../api/client';

export const useAnalysis = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [processingTime, setProcessingTime] = useState(0);

  const generateData = async (size) => {
    setLoading(true);
    setError(null);
    try {
      const response = await analysisAPI.generateData(size);
      if (response.data.success) {
        setProcessingTime(response.data.processing_time_ms);
        return response.data.data;
      } else {
        setError(response.data.error || 'Failed to generate data');
        return null;
      }
    } catch (err) {
      setError(err.message || 'Failed to generate data');
      return null;
    } finally {
      setLoading(false);
    }
  };

  const runAnalysis = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await analysisAPI.runAnalysis();
      if (response.data.success) {
        setProcessingTime(response.data.processing_time_ms);
        return response.data.data;
      } else {
        setError(response.data.error || 'Failed to run analysis');
        return null;
      }
    } catch (err) {
      setError(err.message || 'Failed to run analysis');
      return null;
    } finally {
      setLoading(false);
    }
  };

  return {
    loading,
    error,
    processingTime,
    generateData,
    runAnalysis
  };
};

export const useDashboard = (autoRefresh = true) => {
  const [stats, setStats] = useState(null);
  const [riskBreakdown, setRiskBreakdown] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [patterns, setPatterns] = useState([]);
  const [chains, setChains] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchAllData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [statsRes, breakdownRes, alertsRes, patternsRes, chainsRes] = await Promise.all([
        dashboardAPI.getStats(),
        dashboardAPI.getRiskBreakdown(),
        dashboardAPI.getAlerts(),
        dashboardAPI.getPatterns(),
        dashboardAPI.getChains()
      ]);

      if (statsRes.data.success) setStats(statsRes.data.data);
      if (breakdownRes.data.success) setRiskBreakdown(breakdownRes.data.data);
      if (alertsRes.data.success) setAlerts(alertsRes.data.data);
      if (patternsRes.data.success) setPatterns(patternsRes.data.data);
      if (chainsRes.data.success) setChains(chainsRes.data.data);
    } catch (err) {
      setError(err.message || 'Failed to fetch dashboard data');
    } finally {
      setLoading(false);
    }
  };

  // Auto-refresh every 10 seconds
  useEffect(() => {
    fetchAllData();

    if (autoRefresh) {
      const interval = setInterval(fetchAllData, 10000);
      return () => clearInterval(interval);
    }
  }, [autoRefresh]);

  return {
    stats,
    riskBreakdown,
    alerts,
    patterns,
    chains,
    loading,
    error,
    refetch: fetchAllData
  };
};
