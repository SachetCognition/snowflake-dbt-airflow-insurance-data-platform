"""
Network analysis module for fraud detection in insurance claims.

This module implements graph-based fraud detection:
1. Customer relationship graphs
2. Connected claims analysis
3. Fraud ring detection
4. Suspicious pattern identification through network metrics
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict

try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False
    print("Warning: networkx not installed. Network analysis features will be limited.")

import snowflake.connector
from dotenv import load_dotenv

load_dotenv()


class FraudNetworkAnalyzer:
    """Network-based fraud detection using graph analysis."""
    
    def __init__(self, conn=None):
        """Initialize the network analyzer.
        
        Args:
            conn: Optional Snowflake connection
        """
        self.conn = conn or self._create_connection()
        self.customer_graph = None
        self.claim_graph = None
        self.policy_graph = None
    
    def _create_connection(self):
        """Create Snowflake connection."""
        return snowflake.connector.connect(
            account=os.environ.get('SNOWFLAKE_ACCOUNT'),
            user=os.environ.get('SNOWFLAKE_USER'),
            password=os.environ.get('SNOWFLAKE_PASSWORD'),
            role=os.environ.get('SNOWFLAKE_ROLE'),
            warehouse=os.environ.get('SNOWFLAKE_WAREHOUSE'),
            database='INSURANCE_DB'
        )
    
    def build_customer_claim_graph(self) -> 'nx.Graph':
        """Build a graph connecting customers through shared claim patterns.
        
        Customers are connected if they have:
        - Claims with similar amounts (within 10%)
        - Claims on the same day
        - Same claim cause
        
        Returns:
            NetworkX graph of customer relationships
        """
        if not NETWORKX_AVAILABLE:
            raise ImportError("networkx is required for network analysis")
        
        # Load claims data
        query = """
        SELECT 
            c.claim_id,
            c.customer_id,
            c.policy_id,
            c.loss_date,
            c.report_date,
            c.claim_cause,
            c.incurred_amount,
            ps.product,
            ps.channel
        FROM INSURANCE_DB.RAW.CLAIMS c
        JOIN INSURANCE_DB.RAW_CORE.CORE_POLICY_SNAPSHOT ps ON c.policy_id = ps.policy_id
        """
        cursor = self.conn.cursor()
        cursor.execute(query)
        columns = [desc[0].lower() for desc in cursor.description]
        data = cursor.fetchall()
        cursor.close()
        
        claims_df = pd.DataFrame(data, columns=columns)
        
        # Build graph
        G = nx.Graph()
        
        # Add customer nodes
        for customer_id in claims_df['customer_id'].unique():
            customer_claims = claims_df[claims_df['customer_id'] == customer_id]
            G.add_node(
                f"C_{customer_id}",
                node_type='customer',
                customer_id=customer_id,
                claim_count=len(customer_claims),
                total_incurred=customer_claims['incurred_amount'].sum()
            )
        
        # Connect customers with similar claim patterns
        customers = claims_df['customer_id'].unique()
        
        for i, cust1 in enumerate(customers):
            claims1 = claims_df[claims_df['customer_id'] == cust1]
            
            for cust2 in customers[i+1:]:
                claims2 = claims_df[claims_df['customer_id'] == cust2]
                
                # Check for connections
                connection_score = 0
                connection_reasons = []
                
                # Same day claims
                dates1 = set(claims1['loss_date'].astype(str))
                dates2 = set(claims2['loss_date'].astype(str))
                common_dates = dates1 & dates2
                if common_dates:
                    connection_score += len(common_dates) * 10
                    connection_reasons.append(f"same_day_claims:{len(common_dates)}")
                
                # Same claim cause
                causes1 = set(claims1['claim_cause'])
                causes2 = set(claims2['claim_cause'])
                common_causes = causes1 & causes2
                if common_causes:
                    connection_score += len(common_causes) * 5
                    connection_reasons.append(f"same_causes:{len(common_causes)}")
                
                # Similar amounts (within 10%)
                for amt1 in claims1['incurred_amount']:
                    for amt2 in claims2['incurred_amount']:
                        if amt1 > 0 and abs(amt1 - amt2) / amt1 < 0.1:
                            connection_score += 3
                            connection_reasons.append("similar_amount")
                            break
                    if "similar_amount" in connection_reasons:
                        break
                
                # Add edge if connection score is significant
                if connection_score >= 10:
                    G.add_edge(
                        f"C_{cust1}",
                        f"C_{cust2}",
                        weight=connection_score,
                        reasons=connection_reasons
                    )
        
        self.customer_graph = G
        return G
    
    def detect_fraud_rings(self, min_size: int = 3) -> List[Dict]:
        """Detect potential fraud rings (connected customer groups).
        
        Args:
            min_size: Minimum number of customers in a ring
            
        Returns:
            List of detected fraud rings with details
        """
        if self.customer_graph is None:
            self.build_customer_claim_graph()
        
        if not NETWORKX_AVAILABLE:
            return []
        
        # Find connected components
        components = list(nx.connected_components(self.customer_graph))
        
        fraud_rings = []
        for component in components:
            if len(component) >= min_size:
                # Analyze the component
                subgraph = self.customer_graph.subgraph(component)
                
                # Calculate network metrics
                density = nx.density(subgraph)
                avg_clustering = nx.average_clustering(subgraph)
                
                # Get customer details
                customer_ids = [
                    self.customer_graph.nodes[n]['customer_id'] 
                    for n in component
                ]
                total_claims = sum(
                    self.customer_graph.nodes[n]['claim_count'] 
                    for n in component
                )
                total_incurred = sum(
                    self.customer_graph.nodes[n]['total_incurred'] 
                    for n in component
                )
                
                # Calculate ring risk score
                risk_score = self._calculate_ring_risk_score(
                    len(component), density, avg_clustering, total_claims
                )
                
                fraud_rings.append({
                    'ring_id': len(fraud_rings) + 1,
                    'customer_count': len(component),
                    'customer_ids': customer_ids,
                    'total_claims': total_claims,
                    'total_incurred': total_incurred,
                    'network_density': round(density, 4),
                    'clustering_coefficient': round(avg_clustering, 4),
                    'risk_score': risk_score,
                    'risk_tier': 'HIGH' if risk_score >= 70 else 'MEDIUM' if risk_score >= 40 else 'LOW'
                })
        
        # Sort by risk score
        fraud_rings.sort(key=lambda x: x['risk_score'], reverse=True)
        
        return fraud_rings
    
    def _calculate_ring_risk_score(
        self, 
        size: int, 
        density: float, 
        clustering: float, 
        claim_count: int
    ) -> int:
        """Calculate risk score for a potential fraud ring.
        
        Args:
            size: Number of customers in ring
            density: Network density
            clustering: Clustering coefficient
            claim_count: Total claims in ring
            
        Returns:
            Risk score (0-100)
        """
        score = 0
        
        # Size factor (larger rings are more suspicious)
        if size >= 5:
            score += 25
        elif size >= 3:
            score += 15
        
        # Density factor (highly connected groups are suspicious)
        if density >= 0.7:
            score += 25
        elif density >= 0.5:
            score += 15
        elif density >= 0.3:
            score += 10
        
        # Clustering factor
        if clustering >= 0.7:
            score += 20
        elif clustering >= 0.5:
            score += 10
        
        # Claims per customer
        claims_per_customer = claim_count / size if size > 0 else 0
        if claims_per_customer >= 3:
            score += 20
        elif claims_per_customer >= 2:
            score += 10
        
        return min(score, 100)
    
    def analyze_claim_velocity_network(self, time_window_days: int = 30) -> pd.DataFrame:
        """Analyze claims that occur in clusters within time windows.
        
        Args:
            time_window_days: Time window for clustering
            
        Returns:
            DataFrame with velocity network analysis
        """
        query = f"""
        WITH claim_pairs AS (
            SELECT 
                c1.claim_id as claim1_id,
                c1.customer_id as customer1_id,
                c2.claim_id as claim2_id,
                c2.customer_id as customer2_id,
                c1.loss_date as loss_date1,
                c2.loss_date as loss_date2,
                ABS(DATEDIFF('day', c1.loss_date, c2.loss_date)) as days_apart,
                c1.claim_cause as cause1,
                c2.claim_cause as cause2,
                c1.incurred_amount as amount1,
                c2.incurred_amount as amount2
            FROM INSURANCE_DB.RAW.CLAIMS c1
            JOIN INSURANCE_DB.RAW.CLAIMS c2 
                ON c1.claim_id < c2.claim_id
                AND ABS(DATEDIFF('day', c1.loss_date, c2.loss_date)) <= {time_window_days}
        )
        SELECT 
            customer1_id,
            customer2_id,
            COUNT(*) as pair_count,
            AVG(days_apart) as avg_days_apart,
            SUM(amount1 + amount2) as total_amount,
            LISTAGG(DISTINCT cause1, ',') as causes
        FROM claim_pairs
        GROUP BY customer1_id, customer2_id
        HAVING COUNT(*) >= 2
        ORDER BY pair_count DESC
        """
        
        cursor = self.conn.cursor()
        cursor.execute(query)
        columns = [desc[0].lower() for desc in cursor.description]
        data = cursor.fetchall()
        cursor.close()
        
        return pd.DataFrame(data, columns=columns)
    
    def get_customer_network_metrics(self) -> pd.DataFrame:
        """Calculate network-based fraud metrics for each customer.
        
        Returns:
            DataFrame with customer network metrics
        """
        if self.customer_graph is None:
            self.build_customer_claim_graph()
        
        if not NETWORKX_AVAILABLE:
            return pd.DataFrame()
        
        metrics = []
        
        for node in self.customer_graph.nodes():
            if self.customer_graph.nodes[node].get('node_type') == 'customer':
                customer_id = self.customer_graph.nodes[node]['customer_id']
                
                # Calculate centrality metrics
                degree = self.customer_graph.degree(node)
                
                # Get neighbors
                neighbors = list(self.customer_graph.neighbors(node))
                
                # Calculate local clustering
                if len(neighbors) >= 2:
                    local_clustering = nx.clustering(self.customer_graph, node)
                else:
                    local_clustering = 0
                
                # Sum of edge weights (connection strength)
                total_connection_strength = sum(
                    self.customer_graph[node][neighbor].get('weight', 0)
                    for neighbor in neighbors
                )
                
                # Network risk score
                network_risk = self._calculate_customer_network_risk(
                    degree, local_clustering, total_connection_strength
                )
                
                metrics.append({
                    'customer_id': customer_id,
                    'degree_centrality': degree,
                    'connected_customers': len(neighbors),
                    'local_clustering': round(local_clustering, 4),
                    'connection_strength': total_connection_strength,
                    'network_risk_score': network_risk,
                    'network_risk_tier': 'HIGH' if network_risk >= 60 else 'MEDIUM' if network_risk >= 30 else 'LOW'
                })
        
        return pd.DataFrame(metrics)
    
    def _calculate_customer_network_risk(
        self, 
        degree: int, 
        clustering: float, 
        connection_strength: float
    ) -> int:
        """Calculate network-based risk score for a customer.
        
        Args:
            degree: Number of connections
            clustering: Local clustering coefficient
            connection_strength: Sum of edge weights
            
        Returns:
            Risk score (0-100)
        """
        score = 0
        
        # Degree factor
        if degree >= 5:
            score += 30
        elif degree >= 3:
            score += 20
        elif degree >= 1:
            score += 10
        
        # Clustering factor
        if clustering >= 0.7:
            score += 25
        elif clustering >= 0.5:
            score += 15
        elif clustering >= 0.3:
            score += 10
        
        # Connection strength factor
        if connection_strength >= 50:
            score += 30
        elif connection_strength >= 30:
            score += 20
        elif connection_strength >= 15:
            score += 10
        
        return min(score, 100)
    
    def find_suspicious_patterns(self) -> List[Dict]:
        """Identify suspicious network patterns.
        
        Returns:
            List of suspicious patterns with details
        """
        patterns = []
        
        if self.customer_graph is None:
            self.build_customer_claim_graph()
        
        if not NETWORKX_AVAILABLE:
            return patterns
        
        # Pattern 1: Star patterns (one customer connected to many)
        for node in self.customer_graph.nodes():
            degree = self.customer_graph.degree(node)
            if degree >= 5:
                neighbors = list(self.customer_graph.neighbors(node))
                # Check if neighbors are not connected to each other
                neighbor_edges = sum(
                    1 for i, n1 in enumerate(neighbors) 
                    for n2 in neighbors[i+1:] 
                    if self.customer_graph.has_edge(n1, n2)
                )
                max_possible_edges = len(neighbors) * (len(neighbors) - 1) / 2
                
                if max_possible_edges > 0 and neighbor_edges / max_possible_edges < 0.3:
                    patterns.append({
                        'pattern_type': 'STAR',
                        'center_customer': self.customer_graph.nodes[node]['customer_id'],
                        'connected_count': degree,
                        'description': f'Customer connected to {degree} others with low inter-connectivity',
                        'risk_level': 'HIGH'
                    })
        
        # Pattern 2: Cliques (fully connected groups)
        cliques = list(nx.find_cliques(self.customer_graph))
        for clique in cliques:
            if len(clique) >= 3:
                customer_ids = [
                    self.customer_graph.nodes[n]['customer_id'] 
                    for n in clique
                ]
                patterns.append({
                    'pattern_type': 'CLIQUE',
                    'customer_ids': customer_ids,
                    'size': len(clique),
                    'description': f'Fully connected group of {len(clique)} customers',
                    'risk_level': 'HIGH' if len(clique) >= 4 else 'MEDIUM'
                })
        
        # Pattern 3: Chains (sequential connections)
        # Find paths of length >= 4
        for node in self.customer_graph.nodes():
            for target in self.customer_graph.nodes():
                if node != target:
                    try:
                        paths = list(nx.all_simple_paths(
                            self.customer_graph, node, target, cutoff=5
                        ))
                        for path in paths:
                            if len(path) >= 4:
                                customer_ids = [
                                    self.customer_graph.nodes[n]['customer_id'] 
                                    for n in path
                                ]
                                patterns.append({
                                    'pattern_type': 'CHAIN',
                                    'customer_ids': customer_ids,
                                    'length': len(path),
                                    'description': f'Chain of {len(path)} connected customers',
                                    'risk_level': 'MEDIUM'
                                })
                    except nx.NetworkXNoPath:
                        pass
        
        # Deduplicate patterns
        seen = set()
        unique_patterns = []
        for p in patterns:
            key = (p['pattern_type'], str(sorted(p.get('customer_ids', [p.get('center_customer', '')]))))
            if key not in seen:
                seen.add(key)
                unique_patterns.append(p)
        
        return unique_patterns


def run_network_analysis(output_path: Optional[str] = None) -> Dict:
    """Run complete network analysis for fraud detection.
    
    Args:
        output_path: Optional directory to save results
        
    Returns:
        Dictionary with analysis results
    """
    if not NETWORKX_AVAILABLE:
        print("Error: networkx is required for network analysis")
        print("Install with: pip install networkx")
        return {}
    
    analyzer = FraudNetworkAnalyzer()
    
    print("Building customer-claim network...")
    graph = analyzer.build_customer_claim_graph()
    print(f"Network built: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
    
    print("\nDetecting fraud rings...")
    fraud_rings = analyzer.detect_fraud_rings(min_size=3)
    print(f"Found {len(fraud_rings)} potential fraud rings")
    
    print("\nCalculating customer network metrics...")
    customer_metrics = analyzer.get_customer_network_metrics()
    
    print("\nIdentifying suspicious patterns...")
    patterns = analyzer.find_suspicious_patterns()
    print(f"Found {len(patterns)} suspicious patterns")
    
    results = {
        'network_stats': {
            'nodes': graph.number_of_nodes(),
            'edges': graph.number_of_edges(),
            'density': nx.density(graph),
            'components': nx.number_connected_components(graph)
        },
        'fraud_rings': fraud_rings,
        'customer_metrics': customer_metrics,
        'suspicious_patterns': patterns,
        'analyzed_at': datetime.now().isoformat()
    }
    
    if output_path:
        os.makedirs(output_path, exist_ok=True)
        
        # Save fraud rings
        if fraud_rings:
            pd.DataFrame(fraud_rings).to_csv(
                os.path.join(output_path, 'fraud_rings.csv'), index=False
            )
        
        # Save customer metrics
        if not customer_metrics.empty:
            customer_metrics.to_csv(
                os.path.join(output_path, 'customer_network_metrics.csv'), index=False
            )
        
        # Save patterns
        if patterns:
            pd.DataFrame(patterns).to_csv(
                os.path.join(output_path, 'suspicious_patterns.csv'), index=False
            )
        
        print(f"\nResults saved to {output_path}")
    
    # Print summary
    print("\n=== Network Analysis Summary ===")
    print(f"Network Density: {results['network_stats']['density']:.4f}")
    print(f"Connected Components: {results['network_stats']['components']}")
    
    if fraud_rings:
        high_risk_rings = [r for r in fraud_rings if r['risk_tier'] == 'HIGH']
        print(f"\nHigh-Risk Fraud Rings: {len(high_risk_rings)}")
        for ring in high_risk_rings[:3]:
            print(f"  Ring {ring['ring_id']}: {ring['customer_count']} customers, "
                  f"score={ring['risk_score']}, ${ring['total_incurred']:,.2f} incurred")
    
    if not customer_metrics.empty:
        high_risk_customers = customer_metrics[customer_metrics['network_risk_tier'] == 'HIGH']
        print(f"\nHigh-Risk Customers (by network): {len(high_risk_customers)}")
    
    return results


if __name__ == "__main__":
    results = run_network_analysis()
    print("\nNetwork analysis complete!")
