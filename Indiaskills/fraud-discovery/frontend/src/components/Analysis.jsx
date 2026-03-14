import React, { useState } from 'react';
import { useAnalysis } from '../hooks/useAnalysis';
import { Play, Zap, BarChart3 } from 'lucide-react';
import toast from 'react-hot-toast';

export default function Analysis() {
  const { loading, error, processingTime, generateData, runAnalysis } = useAnalysis();
  const [dataSize, setDataSize] = useState(10000);
  const [analysisComplete, setAnalysisComplete] = useState(false);
  const [result, setResult] = useState(null);

  const handleGenerateData = async () => {
    try {
      const result = await generateData(dataSize);
      if (result) {
        toast.success(`Generated ${result.generated_count} transactions (${(result.fraud_rate * 100).toFixed(1)}% fraud rate)`);
        setAnalysisComplete(false);
        setResult(null);
      }
    } catch (err) {
      toast.error('Failed to generate data');
    }
  };

  const handleRunAnalysis = async () => {
    try {
      const result = await runAnalysis();
      if (result) {
        setResult(result);
        setAnalysisComplete(true);
        toast.success('Analysis completed successfully');
      }
    } catch (err) {
      toast.error('Failed to run analysis');
    }
  };

  return (
    <div className="space-y-6 animate-fadeIn">
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-white mb-2">Analysis Control</h1>
        <p className="text-slate-400">Generate synthetic data and run the fraud detection pipeline</p>
      </div>

      {error && (
        <div className="bg-red-900/20 border border-red-700 rounded-lg p-4 text-red-200">
          {error}
        </div>
      )}

      {/* Data Generation Section */}
      <div className="bg-slate-800 border border-slate-700 rounded-lg p-6">
        <h2 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
          <Zap className="w-5 h-5 text-orange-500" />
          Step 1: Generate Synthetic Data
        </h2>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Number of Transactions: {dataSize.toLocaleString()}
            </label>
            <input
              type="range"
              min="1000"
              max="100000"
              step="1000"
              value={dataSize}
              onChange={(e) => setDataSize(parseInt(e.target.value))}
              className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer"
            />
            <div className="flex justify-between text-xs text-slate-400 mt-2">
              <span>1K</span>
              <span>25K</span>
              <span>50K</span>
              <span>75K</span>
              <span>100K</span>
            </div>
          </div>

          <div className="bg-slate-700/30 rounded p-4 text-sm text-slate-300">
            <p><span className="font-semibold">Will generate:</span> {dataSize.toLocaleString()} transactions</p>
            <p><span className="font-semibold">Expected fraud rate:</span> 5%</p>
            <p><span className="font-semibold">Expected fraudulent transactions:</span> ~{(dataSize * 0.05).toLocaleString()}</p>
          </div>

          <button
            onClick={handleGenerateData}
            disabled={loading}
            className="w-full px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-semibold rounded-lg transition-colors flex items-center justify-center gap-2"
          >
            <Play className="w-4 h-4" />
            {loading ? 'Generating...' : 'Generate Data'}
          </button>

          {processingTime > 0 && (
            <p className="text-sm text-slate-400">
              Processing time: {(processingTime / 1000).toFixed(2)}s
            </p>
          )}
        </div>
      </div>

      {/* Analysis Section */}
      <div className="bg-slate-800 border border-slate-700 rounded-lg p-6">
        <h2 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-orange-500" />
          Step 2: Run Fraud Detection Analysis
        </h2>

        <div className="space-y-4">
          <p className="text-sm text-slate-300">
            Executes the complete pipeline:
          </p>
          <ul className="text-sm text-slate-400 space-y-2 ml-4">
            <li>✓ Feature engineering and normalization</li>
            <li>✓ Ensemble anomaly detection (Isolation Forest + DBSCAN + Z-Score)</li>
            <li>✓ Fraud pattern discovery and clustering</li>
            <li>✓ Suspicious transaction chain analysis</li>
          </ul>

          <button
            onClick={handleRunAnalysis}
            disabled={loading}
            className="w-full px-6 py-3 bg-orange-600 hover:bg-orange-700 disabled:opacity-50 text-white font-semibold rounded-lg transition-colors flex items-center justify-center gap-2"
          >
            <Zap className="w-4 h-4" />
            {loading ? 'Analyzing...' : 'Run Analysis'}
          </button>

          {processingTime > 0 && (
            <p className="text-sm text-slate-400">
              Processing time: {(processingTime / 1000).toFixed(2)}s
            </p>
          )}
        </div>
      </div>

      {/* Results Section */}
      {analysisComplete && result && (
        <div className="bg-gradient-to-r from-green-900/20 to-teal-900/20 border border-green-700 rounded-lg p-6">
          <h2 className="text-xl font-semibold text-white mb-4">✓ Analysis Complete!</h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-slate-800 rounded p-4 border border-slate-700">
              <p className="text-slate-400 text-sm mb-1">Total Transactions</p>
              <p className="text-2xl font-bold text-white">{result.total_transactions?.toLocaleString()}</p>
            </div>

            <div className="bg-slate-800 rounded p-4 border border-slate-700">
              <p className="text-slate-400 text-sm mb-1">Flagged as Suspicious</p>
              <p className="text-2xl font-bold text-orange-400">{result.flagged_count?.toLocaleString()}</p>
            </div>

            <div className="bg-slate-800 rounded p-4 border border-slate-700">
              <p className="text-slate-400 text-sm mb-1">Fraud Patterns Discovered</p>
              <p className="text-2xl font-bold text-blue-400">{result.detected_patterns}</p>
            </div>

            <div className="bg-slate-800 rounded p-4 border border-slate-700">
              <p className="text-slate-400 text-sm mb-1">Suspicious Chains Detected</p>
              <p className="text-2xl font-bold text-purple-400">{result.detected_chains}</p>
            </div>
          </div>

          <div className="mt-4 p-4 bg-slate-700/30 rounded">
            <p className="text-sm text-slate-300">
              <span className="font-semibold">Processing Time:</span> {(result.processing_time_ms / 1000).toFixed(2)}s
            </p>
            <p className="text-sm text-slate-300 mt-1">
              Check the <span className="font-semibold">Dashboard</span>, <span className="font-semibold">Patterns</span>, and <span className="font-semibold">Chains</span> pages to explore the results.
            </p>
          </div>
        </div>
      )}

      {/* Information Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-4">
          <h3 className="font-semibold text-white mb-2">Isolation Forest</h3>
          <p className="text-sm text-slate-400">
            Detects outliers by randomly isolating features. Highly effective for fraud detection.
          </p>
        </div>

        <div className="bg-slate-800 border border-slate-700 rounded-lg p-4">
          <h3 className="font-semibold text-white mb-2">DBSCAN Clustering</h3>
          <p className="text-sm text-slate-400">
            Groups similar anomalies together. Identifies novel fraud signatures.
          </p>
        </div>

        <div className="bg-slate-800 border border-slate-700 rounded-lg p-4">
          <h3 className="font-semibold text-white mb-2">Statistical Z-Score</h3>
          <p className="text-sm text-slate-400">
            Flags extreme deviations from user baselines. Catches behavioral anomalies.
          </p>
        </div>
      </div>

      {/* Performance Notes */}
      <div className="bg-slate-800 border border-slate-700 rounded-lg p-6 text-sm">
        <h3 className="font-semibold text-white mb-3">Performance Notes</h3>
        <ul className="text-slate-400 space-y-2 ml-4">
          <li>
            <span className="font-semibold">Feature Engineering:</span> Takes ~1-2 seconds for 10K transactions
          </li>
          <li>
            <span className="font-semibold">Anomaly Detection:</span> Ensemble inference is real-time (&lt;100ms per batch)
          </li>
          <li>
            <span className="font-semibold">Pattern Mining:</span> DBSCAN clustering scales to 100K+ transactions
          </li>
          <li>
            <span className="font-semibold">Chain Analysis:</span> Network algorithms optimal for &lt;10K entities
          </li>
        </ul>
      </div>
    </div>
  );
}
