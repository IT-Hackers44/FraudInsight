import React, { useState, useEffect } from 'react';
import { dashboardAPI } from '../api/client';
import { Network, RefreshCw } from 'lucide-react';

export default function Chains() {
  const [chains, setChains] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedChain, setSelectedChain] = useState(null);

  useEffect(() => {
    fetchChains();
  }, []);

  const fetchChains = async () => {
    try {
      setLoading(true);
      const response = await dashboardAPI.getChains();
      if (response.data.success) {
        setChains(response.data.data || []);
      } else {
        setError(response.data.error || 'Failed to fetch chains');
      }
    } catch (err) {
      setError(err.message || 'Failed to fetch chains');
    } finally {
      setLoading(false);
    }
  };

  const getChainTypeIcon = (type) => {
    switch (type) {
      case 'CYCLE':
        return '🔄';
      case 'STAR':
        return '⭐';
      case 'FUNNEL':
        return '📊';
      default:
        return '🔗';
    }
  };

  const getChainTypeDescription = (type) => {
    switch (type) {
      case 'CYCLE':
        return 'Money Cycle: Circular transaction pattern A→B→C→A';
      case 'STAR':
        return 'Money Mule Network: One sender to many receivers';
      case 'FUNNEL':
        return 'Fund Aggregation: Many senders to one receiver';
      default:
        return 'Transaction Chain';
    }
  };

  const renderSimpleGraph = (chain) => {
    // Create a simple text-based visualization
    const nodeIds = new Set();
    chain.nodes?.forEach(n => nodeIds.add(n.id));

    return (
      <div className="space-y-2">
        {chain.edges?.slice(0, 10).map((edge, idx) => (
          <div key={idx} className="text-xs font-mono text-slate-400">
            <span className="text-blue-400">{edge.source?.split('_')[1]}</span>
            {' → '}
            <span className="text-orange-400">{edge.target?.split('_')[1]}</span>
            {' '}
            <span className="text-green-400">${edge.amount?.toFixed(0)}</span>
          </div>
        ))}
        {chain.edges?.length > 10 && (
          <div className="text-xs text-slate-500">... and {chain.edges.length - 10} more</div>
        )}
      </div>
    );
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
        <h1 className="text-4xl font-bold text-white mb-2">Transaction Chains</h1>
        <p className="text-slate-400">Suspicious transaction patterns: cycles,money mule networks, and fund aggregation</p>
      </div>

      <div className="flex gap-2">
        <button
          onClick={fetchChains}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {loading ? (
        <div className="space-y-4">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-48 bg-slate-700/50 rounded-lg animate-pulse" />
          ))}
        </div>
      ) : chains.length === 0 ? (
        <div className="text-center py-12 text-slate-400">
          <p>No suspicious chains detected. Run analysis first.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {chains.map((chain, idx) => (
            <div
              key={idx}
              className={`bg-slate-800 border rounded-lg p-6 cursor-pointer transition-all ${
                selectedChain === idx
                  ? 'border-orange-500 shadow-lg shadow-orange-500/20'
                  : 'border-slate-700 hover:border-slate-600'
              }`}
              onClick={() => setSelectedChain(selectedChain === idx ? null : idx)}
            >
              {/* Header */}
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <span className="text-2xl">{getChainTypeIcon(chain.chain_type)}</span>
                    <div>
                      <h3 className="font-semibold text-white">{getChainTypeDescription(chain.chain_type)}</h3>
                      <p className="text-sm text-slate-400">{chain.description}</p>
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <p className={`inline-block px-3 py-1 rounded text-xs font-semibold ${
                    chain.risk_score >= 0.85 ? 'bg-red-900/50 text-red-200' :
                    chain.risk_score >= 0.65 ? 'bg-orange-900/50 text-orange-200' :
                    chain.risk_score >= 0.40 ? 'bg-yellow-900/50 text-yellow-200' :
                    'bg-green-900/50 text-green-200'
                  }`}>
                    Risk: {(chain.risk_score * 100).toFixed(0)}%
                  </p>
                </div>
              </div>

              {/* Statistics */}
              <div className="grid grid-cols-4 gap-3 mb-4 pb-4 border-b border-slate-700">
                <div>
                  <p className="text-slate-400 text-xs">Nodes</p>
                  <p className="text-white font-bold">{chain.nodes?.length || 0}</p>
                </div>
                <div>
                  <p className="text-slate-400 text-xs">Transactions</p>
                  <p className="text-white font-bold">{chain.transaction_count}</p>
                </div>
                <div>
                  <p className="text-slate-400 text-xs">Total Amount</p>
                  <p className="text-green-400 font-bold">${(chain.total_amount || 0).toFixed(0)}</p>
                </div>
                <div>
                  <p className="text-slate-400 text-xs">Chain Type</p>
                  <p className="text-white font-bold">{chain.chain_type}</p>
                </div>
              </div>

              {/* Expanded view */}
              {selectedChain === idx && (
                <div className="mt-4 pt-4 border-t border-slate-700 space-y-4">
                  <div>
                    <p className="text-sm font-semibold text-white mb-2">Transaction Flow</p>
                    <div className="bg-slate-700/30 rounded p-4 max-h-48 overflow-y-auto">
                      {renderSimpleGraph(chain)}
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-sm font-semibold text-white mb-2">Entities in Chain</p>
                      <div className="text-xs space-y-1 max-h-32 overflow-y-auto">
                        {chain.nodes?.slice(0, 10).map((node, i) => (
                          <div key={i} className="flex items-center gap-2 text-slate-300">
                            <span className={`w-2 h-2 rounded-full ${
                              node.type === 'user' ? 'bg-blue-500' : 'bg-orange-500'
                            }`} />
                            <span className="font-mono">{node.label}</span>
                            <span className="text-slate-500 text-xs">({node.type})</span>
                          </div>
                        ))}
                        {chain.nodes?.length > 10 && (
                          <div className="text-slate-500 text-xs">
                            ... and {chain.nodes.length - 10} more
                          </div>
                        )}
                      </div>
                    </div>

                    <div>
                      <p className="text-sm font-semibold text-white mb-2">Risk Assessment</p>
                      <div className="text-xs text-slate-300 space-y-2">
                        <p>
                          <span className="font-semibold">Severity:</span>{' '}
                          <span className={chain.risk_score >= 0.85 ? 'text-red-400' : 'text-orange-400'}>
                            {chain.risk_score >= 0.85 ? 'CRITICAL' : chain.risk_score >= 0.65 ? 'HIGH' : 'MEDIUM'}
                          </span>
                        </p>
                        <p>
                          <span className="font-semibold">Avg Tx Amount:</span> ${
                            chain.total_amount && chain.transaction_count
                              ? (chain.total_amount / chain.transaction_count).toFixed(2)
                              : 0
                          }
                        </p>
                        <p>
                          <span className="font-semibold">Discovered:</span>{' '}
                          {new Date(chain.created_at).toLocaleDateString()}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Legend */}
      <div className="bg-slate-800 border border-slate-700 rounded-lg p-4">
        <p className="text-sm font-semibold text-white mb-3">Legend</p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
          <div className="flex items-center gap-2">
            <span className="text-2xl">🔄</span>
            <div>
              <p className="font-semibold text-white">Money Cycle</p>
              <p className="text-xs text-slate-400">A→B→C→A pattern within 24h</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-2xl">⭐</span>
            <div>
              <p className="font-semibold text-white">Star Network</p>
              <p className="text-xs text-slate-400">1 sender to 10+ receivers</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-2xl">📊</span>
            <div>
              <p className="font-semibold text-white">Funnel</p>
              <p className="text-xs text-slate-400">10+ senders to 1 receiver</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
