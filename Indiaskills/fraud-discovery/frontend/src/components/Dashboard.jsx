import React, { useState } from 'react';
import { useDashboard } from '../hooks/useAnalysis';
import { BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { AlertTriangle, TrendingUp, AlertCircle, CheckCircle, Clock } from 'lucide-react';
import toast from 'react-hot-toast';

export default function Dashboard() {
  const { stats, riskBreakdown, alerts, patterns, loading, error } = useDashboard(true);
  const [expandedAlert, setExpandedAlert] = useState(null);

  if (error) {
    return (
      <div className="rounded-lg bg-red-900/20 border border-red-700 p-4 text-red-200">
        <p className="font-semibold">Error loading dashboard: {error}</p>
      </div>
    );
  }

  const riskTierChartData = riskBreakdown ? [
    { name: 'Critical', value: riskBreakdown.CRITICAL || 0, fill: '#ef4444' },
    { name: 'High', value: riskBreakdown.HIGH || 0, fill: '#f97316' },
    { name: 'Medium', value: riskBreakdown.MEDIUM || 0, fill: '#eab308' },
    { name: 'Low', value: riskBreakdown.LOW || 0, fill: '#22c55e' }
  ] : [];

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-white mb-2">Dashboard</h1>
        <p className="text-slate-400">Real-time fraud detection overview and analytics</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon={<TrendingUp className="w-5 h-5" />}
          label="Total Transactions"
          value={loading ? '...' : stats?.total_transactions || 0}
          color="text-blue-400"
        />
        <StatCard
          icon={<AlertTriangle className="w-5 h-5" />}
          label="Flagged"
          value={loading ? '...' : stats?.flagged_count || 0}
          color="text-orange-400"
        />
        <StatCard
          icon={<AlertCircle className="w-5 h-5" />}
          label="Critical Alerts"
          value={loading ? '...' : stats?.critical_count || 0}
          color="text-red-400"
        />
        <StatCard
          icon={<CheckCircle className="w-5 h-5" />}
          label="Detection Rate"
          value={loading ? '...' : `${stats?.detection_rate || 0}%`}
          color="text-green-400"
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Risk Breakdown Pie Chart */}
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Risk Tier Distribution</h2>
          {loading ? (
            <div className="h-64 bg-slate-700/50 rounded animate-pulse" />
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={riskTierChartData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, value }) => `${name}: ${value}`}
                  outerRadius={100}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {riskTierChartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.fill} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Top Fraud Types */}
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Top Fraud Patterns</h2>
          {loading ? (
            <div className="space-y-2">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="h-10 bg-slate-700/50 rounded animate-pulse" />
              ))}
            </div>
          ) : (
            <div className="space-y-3">
              {stats?.top_fraud_types?.slice(0, 5).map((pattern, idx) => (
                <div key={idx} className="flex items-center justify-between p-3 bg-slate-700/30 rounded border border-slate-600">
                  <div className="flex-1">
                    <p className="text-sm font-medium text-white">{pattern.name.substring(0, 40)}</p>
                    <p className="text-xs text-slate-400">{pattern.count} transactions</p>
                  </div>
                  <span className={`px-2 py-1 rounded text-xs font-semibold ${
                    pattern.risk_tier === 'CRITICAL' ? 'bg-red-900/50 text-red-200' :
                    pattern.risk_tier === 'HIGH' ? 'bg-orange-900/50 text-orange-200' :
                    pattern.risk_tier === 'MEDIUM' ? 'bg-yellow-900/50 text-yellow-200' :
                    'bg-green-900/50 text-green-200'
                  }`}>
                    {pattern.risk_tier}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Real-time Alerts Feed */}
      <div className="bg-slate-800 border border-slate-700 rounded-lg p-6">
        <div className="flex items-center gap-2 mb-4">
          <Clock className="w-5 h-5 text-orange-500" />
          <h2 className="text-lg font-semibold text-white">Recent High-Risk Alerts</h2>
        </div>

        {loading ? (
          <div className="space-y-2">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-12 bg-slate-700/50 rounded animate-pulse" />
            ))}
          </div>
        ) : alerts && alerts.length > 0 ? (
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {alerts.slice(0, 10).map((alert, idx) => (
              <div
                key={idx}
                className={`p-3 rounded-lg border cursor-pointer transition-all hover:border-orange-500 ${
                  alert.risk_tier === 'CRITICAL'
                    ? 'bg-red-900/20 border-red-700'
                    : 'bg-orange-900/20 border-orange-700'
                }`}
                onClick={() => setExpandedAlert(expandedAlert === idx ? null : idx)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <p className="text-sm font-mono text-white">{alert.transaction_id}</p>
                    <p className="text-xs text-slate-400">User: {alert.user_id} | Amount: ${alert.amount}</p>
                  </div>
                  <span className={`px-2 py-1 rounded text-xs font-semibold ${
                    alert.risk_tier === 'CRITICAL'
                      ? 'bg-red-900 text-red-100'
                      : 'bg-orange-900 text-orange-100'
                  }`}>
                    {alert.risk_tier}
                  </span>
                </div>

                {expandedAlert === idx && (
                  <div className="mt-3 pt-3 border-t border-slate-600 text-xs text-slate-300">
                    <p><span className="font-semibold">Reason:</span> {alert.explanation}</p>
                    <p className="mt-2"><span className="font-semibold">Time:</span> {new Date(alert.timestamp).toLocaleString()}</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-slate-400 text-center py-8">No recent alerts detected</p>
        )}
      </div>

      {/* Statistics Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-6">
          <p className="text-slide-400 text-sm mb-2">False Positive Rate</p>
          <p className="text-3xl font-bold text-yellow-400">{stats?.false_positive_estimate || 0}%</p>
        </div>
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-6">
          <p className="text-slate-400 text-sm mb-2">New Patterns (24h)</p>
          <p className="text-3xl font-bold text-blue-400">{stats?.newly_discovered_patterns || 0}</p>
        </div>
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-6">
          <p className="text-slate-400 text-sm mb-2">Actual Fraud (Known)</p>
          <p className="text-3xl font-bold text-red-400">{stats?.actual_fraud_count || 0}</p>
        </div>
      </div>
    </div>
  );
}

function StatCard({ icon, label, value, color }) {
  return (
    <div className="bg-slate-800 border border-slate-700 rounded-lg p-6 hover:border-orange-500 transition-colors">
      <div className="flex items-center justify-between mb-3">
        <span className={`${color}`}>{icon}</span>
      </div>
      <p className="text-slate-400 text-sm mb-1">{label}</p>
      <p className={`text-2xl font-bold ${color}`}>{value}</p>
    </div>
  );
}
