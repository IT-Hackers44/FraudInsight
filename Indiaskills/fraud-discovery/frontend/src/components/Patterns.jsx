import React, { useState, useEffect } from 'react';
import { dashboardAPI } from '../api/client';
import { TrendingUp, AlertTriangle, Zap } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export default function Patterns() {
  const [patterns, setPatterns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedPattern, setExpandedPattern] = useState(null);

  useEffect(() => {
    fetchPatterns();
  }, []);

  const fetchPatterns = async () => {
    try {
      setLoading(true);
      const response = await dashboardAPI.getPatterns();
      if (response.data.success) {
        setPatterns(response.data.data || []);
      } else {
        setError(response.data.error || 'Failed to fetch patterns');
      }
    } catch (err) {
      setError(err.message || 'Failed to fetch patterns');
    } finally {
      setLoading(false);
    }
  };

  if (error) {
    return (
      <div className="bg-red-900/20 border border-red-700 rounded-lg p-4 text-red-200">
        {error}
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fadeIn">
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-white mb-2">Fraud Patterns</h1>
        <p className="text-slate-400">Discovered emerging fraud signatures and behavioral anomalies</p>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="h-64 bg-slate-700/50 rounded-lg animate-pulse" />
          ))}
        </div>
      ) : patterns.length === 0 ? (
        <div className="text-center py-12 text-slate-400">
          <p>No patterns discovered yet. Run analysis first.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {patterns.map((pattern, idx) => (
            <div
              key={idx}
              className="bg-slate-800 border border-slate-700 rounded-lg p-6 hover:border-orange-500 transition-all cursor-pointer"
              onClick={() => setExpandedPattern(expandedPattern === idx ? null : idx)}
            >
              {/* Header */}
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <Zap className="w-4 h-4 text-orange-500" />
                    <h3 className="font-semibold text-white text-lg">{pattern.name}</h3>
                  </div>
                  <p className={`inline-block px-3 py-1 rounded text-xs font-semibold ${
                    pattern.risk_tier === 'CRITICAL' ? 'bg-red-900/50 text-red-200' :
                    pattern.risk_tier === 'HIGH' ? 'bg-orange-900/50 text-orange-200' :
                    pattern.risk_tier === 'MEDIUM' ? 'bg-yellow-900/50 text-yellow-200' :
                    'bg-green-900/50 text-green-200'
                  }`}>
                    {pattern.risk_tier}
                  </p>
                </div>
                <div className="text-right">
                  {pattern.novelty_score > 0.7 && (
                    <span className="inline-block px-2 py-1 bg-blue-900/50 text-blue-200 rounded text-xs font-semibold mb-2">
                      NEW
                    </span>
                  )}
                </div>
              </div>

              {/* Basic Stats */}
              <div className="grid grid-cols-3 gap-2 mb-4 pb-4 border-b border-slate-700">
                <div>
                  <p className="text-slate-400 text-xs">Transactions</p>
                  <p className="text-white font-bold text-lg">{pattern.transaction_count}</p>
                </div>
                <div>
                  <p className="text-slate-400 text-xs">Severity</p>
                  <p className="text-orange-400 font-bold text-lg">{(pattern.severity_score * 100).toFixed(0)}%</p>
                </div>
                <div>
                  <p className="text-slate-400 text-xs">Novelty</p>
                  <p className="text-blue-400 font-bold text-lg">{(pattern.novelty_score * 100).toFixed(0)}%</p>
                </div>
              </div>

              {/* Description */}
              <p className="text-sm text-slate-300 mb-4 line-clamp-3">{pattern.description}</p>

              {/* Expanded Details */}
              {expandedPattern === idx && pattern.feature_signature && (
                <div className="mt-4 pt-4 border-t border-slate-700 space-y-3">
                  <div>
                    <p className="text-sm font-semibold text-white mb-2">Feature Signature</p>
                    <div className="text-xs text-slate-300 space-y-1">
                      {pattern.feature_signature.avg_amount && (
                        <p>• Avg Amount: ${pattern.feature_signature.avg_amount.toFixed(2)}</p>
                      )}
                      {pattern.feature_signature.avg_velocity_1h !== undefined && (
                        <p>• 1h Velocity: {pattern.feature_signature.avg_velocity_1h} tx/h</p>
                      )}
                      {pattern.feature_signature.is_international !== undefined && (
                        <p>• International: {(pattern.feature_signature.is_international * 100).toFixed(0)}%</p>
                      )}
                      {pattern.feature_signature.common_hours && pattern.feature_signature.common_hours.length > 0 && (
                        <p>• Common Hours: {pattern.feature_signature.common_hours.join(', ')}</p>
                      )}
                    </div>
                  </div>

                  <div>
                    <p className="text-sm font-semibold text-white mb-2">Sample Transactions</p>
                    <div className="bg-slate-700/30 rounded p-2">
                      {pattern.sample_transactions?.slice(0, 3).map((txId, i) => (
                        <p key={i} className="text-xs text-slate-400 font-mono">{txId}</p>
                      ))}
                    </div>
                  </div>

                  <div className="text-xs text-slate-400 pt-2">
                    <p>First Seen: {new Date(pattern.first_seen).toLocaleDateString()}</p>
                    <p>Last Seen: {new Date(pattern.last_seen).toLocaleDateString()}</p>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
