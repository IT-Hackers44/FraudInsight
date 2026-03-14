import React, { useState } from 'react';
import { useTransactions } from '../hooks/useTransactions';
import { ChevronDown, Download, Trash2, Search } from 'lucide-react';
import toast from 'react-hot-toast';

export default function Transactions() {
  const [page, setPage] = useState(1);
  const [searchTerm, setSearchTerm] = useState('');
  const [detailOpen, setDetailOpen] = useState(null);
  const { transactions, loading, error, pagination, refetch, deleteAll } = useTransactions(page, 50);

  const handleExportCSV = () => {
    if (!transactions.length) {
      toast.error('No transactions to export');
      return;
    }

    const headers = Object.keys(transactions[0]);
    const rows = transactions.map(tx =>
      headers.map(h => JSON.stringify(tx[h])).join(',')
    );
    const csv = [headers.join(','), ...rows].join('\n');

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `transactions-${Date.now()}.csv`;
    a.click();
    toast.success('Exported successfully');
  };

  const handleDeleteAll = () => {
    if (window.confirm('Are you sure? This will delete all transactions.')) {
      deleteAll();
      toast.success('All transactions deleted');
    }
  };

  const filteredTransactions = transactions.filter(tx =>
    tx.transaction_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
    tx.user_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
    tx.amount.toString().includes(searchTerm)
  );

  return (
    <div className="space-y-6 animate-fadeIn">
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-white mb-2">Transactions</h1>
        <p className="text-slate-400">Analyze individual transactions and their fraud risk</p>
      </div>

      {/* Controls */}
      <div className="flex flex-col md:flex-row gap-4 bg-slate-800 border border-slate-700 rounded-lg p-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-3 w-4 h-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search by transaction ID, user, or amount..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-slate-700 border border-slate-600 rounded text-white placeholder-slate-400"
          />
        </div>
        <button
          onClick={handleExportCSV}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded transition-colors"
        >
          <Download className="w-4 h-4" />
          Export CSV
        </button>
        <button
          onClick={handleDeleteAll}
          className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white font-semibold rounded transition-colors"
        >
          <Trash2 className="w-4 h-4" />
          Clear All
        </button>
      </div>

      {/* Table */}
      {error && (
        <div className="bg-red-900/20 border border-red-700 rounded-lg p-4 text-red-200">
          Error: {error}
        </div>
      )}

      {loading ? (
        <div className="space-y-2">
          {[...Array(10)].map((_, i) => (
            <div key={i} className="h-12 bg-slate-700/50 rounded animate-pulse" />
          ))}
        </div>
      ) : filteredTransactions.length === 0 ? (
        <div className="text-center py-12 text-slate-400">
          <p>No transactions found. {searchTerm && 'Try adjusting your search.'}</p>
        </div>
      ) : (
        <>
          <div className="overflow-x-auto bg-slate-800 border border-slate-700 rounded-lg">
            <table className="w-full">
              <thead className="bg-slate-700/50 border-b border-slate-600">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-slate-300">ID</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-slate-300">User</th>
                  <th className="px-4 py-3 text-right text-sm font-semibold text-slate-300">Amount</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-slate-300">Merchant</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-slate-300">Time</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-slate-300">Fraud</th>
                  <th className="px-4 py-3 text-center text-sm font-semibold text-slate-300">Details</th>
                </tr>
              </thead>
              <tbody>
                {filteredTransactions.map((tx, idx) => (
                  <React.Fragment key={idx}>
                    <tr className="border-b border-slate-700 hover:bg-slate-700/30 transition-colors">
                      <td className="px-4 py-3 text-sm font-mono text-slate-300">{tx.transaction_id}</td>
                      <td className="px-4 py-3 text-sm text-slate-400">{tx.user_id}</td>
                      <td className="px-4 py-3 text-sm font-semibold text-white text-right">${tx.amount.toFixed(2)}</td>
                      <td className="px-4 py-3 text-sm text-slate-400">{tx.merchant_id}</td>
                      <td className="px-4 py-3 text-sm text-slate-400">
                        {new Date(tx.timestamp).toLocaleDateString()}
                      </td>
                      <td className="px-4 py-3 text-sm">
                        {tx.fraud_label ? (
                          <span className="px-2 py-1 bg-red-900/50 text-red-200 rounded text-xs font-semibold">
                            Yes
                          </span>
                        ) : (
                          <span className="px-2 py-1 bg-green-900/50 text-green-200 rounded text-xs font-semibold">
                            No
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <button
                          onClick={() => setDetailOpen(detailOpen === idx ? null : idx)}
                          className="p-1 hover:bg-slate-600 rounded transition"
                        >
                          <ChevronDown
                            className={`w-4 h-4 text-orange-500 transition-transform ${
                              detailOpen === idx ? 'rotate-180' : ''
                            }`}
                          />
                        </button>
                      </td>
                    </tr>

                    {detailOpen === idx && (
                      <tr className="border-b border-slate-700 bg-slate-700/20">
                        <td colSpan="7" className="px-4 py-4">
                          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                            <div>
                              <p className="text-slate-400 text-xs mb-1">Category</p>
                              <p className="text-white font-semibold">{tx.merchant_category}</p>
                            </div>
                            <div>
                              <p className="text-slate-400 text-xs mb-1">Payment Method</p>
                              <p className="text-white font-semibold">{tx.payment_method}</p>
                            </div>
                            <div>
                              <p className="text-slate-400 text-xs mb-1">Currency</p>
                              <p className="text-white font-semibold">{tx.currency}</p>
                            </div>
                            <div>
                              <p className="text-slate-400 text-xs mb-1">Velocity (1h)</p>
                              <p className="text-white font-semibold">{tx.velocity_1h}</p>
                            </div>
                            <div>
                              <p className="text-slate-400 text-xs mb-1">Velocity (24h)</p>
                              <p className="text-white font-semibold">{tx.velocity_24h}</p>
                            </div>
                            <div>
                              <p className="text-slate-400 text-xs mb-1">International</p>
                              <p className="text-white font-semibold">{tx.is_international ? 'Yes' : 'No'}</p>
                            </div>
                            <div>
                              <p className="text-slate-400 text-xs mb-1">IP Address</p>
                              <p className="text-white font-mono text-xs">{tx.ip_address}</p>
                            </div>
                            <div>
                              <p className="text-slate-400 text-xs mb-1">Device</p>
                              <p className="text-white font-mono text-xs">{tx.device_fingerprint}</p>
                            </div>
                            <div>
                              <p className="text-slate-400 text-xs mb-1">Amount Z-Score</p>
                              <p className="text-white font-semibold">{tx.amount_zscore.toFixed(2)}</p>
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between">
            <div className="text-sm text-slate-400">
              Page {pagination.page} of {pagination.pages} | Total: {pagination.total}
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setPage(Math.max(1, page - 1))}
                disabled={page === 1}
                className="px-4 py-2 bg-slate-700 hover:bg-slate-600 disabled:opacity-50 text-white rounded font-semibold transition"
              >
                Previous
              </button>
              <button
                onClick={() => setPage(page + 1)}
                disabled={page >= pagination.pages}
                className="px-4 py-2 bg-slate-700 hover:bg-slate-600 disabled:opacity-50 text-white rounded font-semibold transition"
              >
                Next
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
