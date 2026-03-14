import networkx as nx
import pandas as pd
import numpy as np
import uuid
from typing import List, Dict, Any, Tuple
from datetime import datetime, timedelta

class ChainAnalyzer:
    def __init__(self):
        """Initialize chain analyzer"""
        self.graph = nx.DiGraph()
        self.discovered_chains = []

    def analyze_chains(self, transactions_df: pd.DataFrame,
                       anomaly_results: List[Dict[str, Any]],
                       time_window_hours: int = 72) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Analyze transaction chains for suspicious patterns.
        Returns (chains_list, graph_data_for_viz)
        """
        self.graph.clear()
        self.discovered_chains = []

        # Filter to suspicious transactions
        suspicious_indices = {r['index'] for r in anomaly_results if r['ensemble_consensus']}

        if not suspicious_indices:
            return [], self._export_graph_data()

        suspicious_df = transactions_df.iloc[list(suspicious_indices)].copy()
        suspicious_df['timestamp'] = pd.to_datetime(suspicious_df['timestamp'])

        # Build directed graph
        for _, row in suspicious_df.iterrows():
            from_node = f"u_{row['user_id']}"
            to_node = f"m_{row['merchant_id']}"

            self.graph.add_node(from_node, node_type='user', id=row['user_id'])
            self.graph.add_node(to_node, node_type='merchant', id=row['merchant_id'])

            self.graph.add_edge(
                from_node, to_node,
                transaction_id=row['transaction_id'],
                amount=row['amount'],
                timestamp=row['timestamp'].isoformat(),
                weight=row['amount']
            )

        # Detect chain patterns
        self._detect_cycles(suspicious_df, time_window_hours)
        self._detect_star_patterns(suspicious_df, time_window_hours)
        self._detect_funnel_patterns(suspicious_df, time_window_hours)

        # Sort by risk score
        self.discovered_chains.sort(key=lambda c: c['risk_score'], reverse=True)

        return self.discovered_chains, self._export_graph_data()

    def _detect_cycles(self, suspicious_df: pd.DataFrame, time_window_hours: int) -> None:
        """Detect cycle patterns: A→B→C→A within time window"""
        time_window = timedelta(hours=time_window_hours)

        # Find all cycles in graph
        try:
            cycles = list(nx.simple_cycles(self.graph))
        except:
            cycles = []

        for cycle in cycles:
            if len(cycle) < 3:
                continue

            # Find transactions matching this cycle
            cycle_txs = []
            for i in range(len(cycle)):
                from_node = cycle[i]
                to_node = cycle[(i + 1) % len(cycle)]

                try:
                    edge_data = self.graph.get_edge_data(from_node, to_node)
                    if edge_data:
                        tx = suspicious_df[suspicious_df['transaction_id'] == edge_data['transaction_id']]
                        if not tx.empty:
                            cycle_txs.append(tx.iloc[0])
                except:
                    pass

            if len(cycle_txs) >= 3:
                # Check if within time window
                cycle_txs_df = pd.DataFrame(cycle_txs)
                cycle_txs_df['timestamp'] = pd.to_datetime(cycle_txs_df['timestamp'])
                time_span = (cycle_txs_df['timestamp'].max() - cycle_txs_df['timestamp'].min())

                if time_span <= time_window:
                    total_amount = cycle_txs_df['amount'].sum()
                    risk_score = min(total_amount / 1000 * 0.5 + 0.5, 1.0)

                    chain = {
                        'chain_id': f"CHAIN_{str(uuid.uuid4())[:8]}",
                        'chain_type': 'CYCLE',
                        'nodes': self._extract_nodes_from_cycle(cycle),
                        'edges': self._extract_edges_from_cycle(cycle_txs),
                        'total_amount': float(total_amount),
                        'transaction_count': len(cycle_txs),
                        'risk_score': risk_score,
                        'description': f"Money cycle detected: {' → '.join([n.split('_')[1][:5] for n in cycle])} → {cycle[0].split('_')[1][:5]}",
                        'transactions': [tx['transaction_id'] for tx in cycle_txs]
                    }

                    self.discovered_chains.append(chain)

    def _detect_star_patterns(self, suspicious_df: pd.DataFrame, time_window_hours: int) -> None:
        """Detect star patterns: 1 sender → many receivers (money mule network)"""
        time_window = timedelta(hours=time_window_hours)

        # Group by user (sender)
        for user_id in suspicious_df['user_id'].unique():
            user_txs = suspicious_df[suspicious_df['user_id'] == user_id].copy()
            user_txs['timestamp'] = pd.to_datetime(user_txs['timestamp'])

            # Check time window
            if (user_txs['timestamp'].max() - user_txs['timestamp'].min()) <= time_window:
                # Count unique merchants
                unique_merchants = user_txs['merchant_id'].nunique()

                if unique_merchants >= 2:
                    total_amount = user_txs['amount'].sum()
                    risk_score = min(unique_merchants / 5 * 0.6 + 0.4, 1.0)

                    nodes = [{'id': f"u_{user_id}", 'type': 'user', 'label': user_id[:8]}]
                    nodes.extend([{'id': f"m_{m}", 'type': 'merchant', 'label': m}
                                 for m in user_txs['merchant_id'].unique()])

                    edges = [{'source': f"u_{user_id}", 'target': f"m_{row['merchant_id']}",
                             'amount': row['amount']}
                            for _, row in user_txs.iterrows()]

                    chain = {
                        'chain_id': f"CHAIN_{str(uuid.uuid4())[:8]}",
                        'chain_type': 'STAR',
                        'nodes': nodes,
                        'edges': edges,
                        'total_amount': float(total_amount),
                        'transaction_count': len(user_txs),
                        'risk_score': risk_score,
                        'description': f"Money mule network: User {user_id} sent to {unique_merchants} merchants in {time_window_hours}h",
                        'transactions': list(user_txs['transaction_id'])
                    }

                    self.discovered_chains.append(chain)

    def _detect_funnel_patterns(self, suspicious_df: pd.DataFrame, time_window_hours: int) -> None:
        """Detect funnel patterns: many senders → 1 receiver (aggregation, layering)"""
        time_window = timedelta(hours=time_window_hours)

        # Group by merchant (receiver)
        for merchant_id in suspicious_df['merchant_id'].unique():
            merchant_txs = suspicious_df[suspicious_df['merchant_id'] == merchant_id].copy()
            merchant_txs['timestamp'] = pd.to_datetime(merchant_txs['timestamp'])

            # Check time window
            if (merchant_txs['timestamp'].max() - merchant_txs['timestamp'].min()) <= time_window:
                unique_users = merchant_txs['user_id'].nunique()

                if unique_users >= 2:
                    total_amount = merchant_txs['amount'].sum()
                    risk_score = min(unique_users / 5 * 0.6 + 0.4, 1.0)

                    nodes = [{'id': f"m_{merchant_id}", 'type': 'merchant', 'label': merchant_id}]
                    nodes.extend([{'id': f"u_{u}", 'type': 'user', 'label': u[:8]}
                                 for u in merchant_txs['user_id'].unique()])

                    edges = [{'source': f"u_{row['user_id']}", 'target': f"m_{merchant_id}",
                             'amount': row['amount']}
                            for _, row in merchant_txs.iterrows()]

                    chain = {
                        'chain_id': f"CHAIN_{str(uuid.uuid4())[:8]}",
                        'chain_type': 'FUNNEL',
                        'nodes': nodes,
                        'edges': edges,
                        'total_amount': float(total_amount),
                        'transaction_count': len(merchant_txs),
                        'risk_score': risk_score,
                        'description': f"Fund aggregation: {unique_users} users funneled to {merchant_id} in {time_window_hours}h",
                        'transactions': list(merchant_txs['transaction_id'])
                    }

                    self.discovered_chains.append(chain)

    def _extract_nodes_from_cycle(self, cycle: List[str]) -> List[Dict[str, Any]]:
        """Extract nodes from cycle for visualization"""
        nodes = []
        for node in cycle:
            node_type = node.split('_')[0]
            node_id = node.split('_')[1]
            nodes.append({
                'id': node,
                'type': 'user' if node_type == 'u' else 'merchant',
                'label': node_id[:8]
            })
        return nodes

    def _extract_edges_from_cycle(self, txs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract edges from transactions"""
        edges = []
        for tx in txs:
            edges.append({
                'source': f"u_{tx['user_id']}",
                'target': f"m_{tx['merchant_id']}",
                'amount': tx['amount'],
                'transaction_id': tx['transaction_id']
            })
        return edges

    def _export_graph_data(self) -> Dict[str, Any]:
        """Export graph data for frontend visualization"""
        nodes = []
        edges = []
        node_ids = set()

        for node, data in self.graph.nodes(data=True):
            node_ids.add(node)
            node_type = data.get('node_type', 'unknown')
            nodes.append({
                'id': node,
                'type': node_type,
                'label': data.get('id', node)[:8],
            })

        for source, target, data in self.graph.edges(data=True):
            edges.append({
                'source': source,
                'target': target,
                'amount': data.get('weight', 0),
                'transaction_id': data.get('transaction_id', ''),
                'label': f"${data.get('weight', 0):.0f}"
            })

        return {
            'nodes': nodes,
            'edges': edges,
            'node_count': len(nodes),
            'edge_count': len(edges)
        }

if __name__ == "__main__":
    analyzer = ChainAnalyzer()
    print("ChainAnalyzer initialized successfully")
