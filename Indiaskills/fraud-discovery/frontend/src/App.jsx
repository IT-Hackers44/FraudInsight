import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import Dashboard from './components/Dashboard';
import Transactions from './components/Transactions';
import Patterns from './components/Patterns';
import Chains from './components/Chains';
import Analysis from './components/Analysis';
import { BarChart3, AlertTriangle, Network, Settings } from 'lucide-react';

import './App.css';

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
        <Toaster position="top-right" />

        {/* Navigation Bar */}
        <nav className="border-b border-slate-700 bg-slate-900/95 backdrop-blur sticky top-0 z-50">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center h-16">
              <Link to="/" className="flex items-center gap-2">
                <AlertTriangle className="w-6 h-6 text-orange-500" />
                <span className="text-xl font-bold text-white">FraudInsight</span>
              </Link>

              <div className="hidden md:flex gap-1">
                <NavLink to="/" icon={BarChart3} label="Dashboard" />
                <NavLink to="/transactions" label="Transactions" />
                <NavLink to="/patterns" label="Patterns" />
                <NavLink to="/chains" icon={Network} label="Chains" />
                <NavLink to="/analysis" icon={Settings} label="Analysis" />
              </div>

              <div className="md:hidden flex gap-2">
                <Link
                  to="/"
                  className="px-3 py-2 rounded-lg text-sm font-medium text-slate-300 hover:bg-slate-800"
                >
                  Home
                </Link>
              </div>
            </div>
          </div>
        </nav>

        {/* Main Content */}
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/transactions" element={<Transactions />} />
            <Route path="/patterns" element={<Patterns />} />
            <Route path="/chains" element={<Chains />} />
            <Route path="/analysis" element={<Analysis />} />
          </Routes>
        </main>

        {/* Footer */}
        <footer className="border-t border-slate-700 bg-slate-900 mt-12 py-6 text-center text-slate-400 text-sm">
          <p>Emerging Cyber Fraud Discovery System v1.0 | Real-time anomaly detection powered by ML</p>
        </footer>
      </div>
    </Router>
  );
}

function NavLink({ to, icon: Icon, label }) {
  return (
    <Link
      to={to}
      className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-slate-300 hover:bg-slate-800 hover:text-white transition-colors"
    >
      {Icon && <Icon className="w-4 h-4" />}
      {label}
    </Link>
  );
}

export default App;
