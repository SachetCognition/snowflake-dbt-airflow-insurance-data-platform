"""
Rule-based fraud detection module for insurance claims.

This module implements various rule-based fraud detection algorithms:
1. Velocity checks - Multiple claims in short time periods
2. Threshold-based anomalies - Unusually high claim amounts
3. Pattern matching - Suspicious claim patterns
4. Timing analysis - Claims shortly after policy inception
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import snowflake.connector
from dotenv import load_dotenv

load_dotenv()


class FraudRuleEngine:
    """Rule-based fraud detection engine for insurance claims."""
    
    def __init__(self, conn=None):
        """Initialize the fraud rule engine.
        
        Args:
            conn: Optional Snowflake connection. If None, creates new connection.
        """
        self.conn = conn or self._create_connection()
        self.rules = []
        self._register_default_rules()
    
    def _create_connection(self):
        """Create Snowflake connection from environment variables."""
        return snowflake.connector.connect(
            account=os.environ.get('SNOWFLAKE_ACCOUNT'),
            user=os.environ.get('SNOWFLAKE_USER'),
            password=os.environ.get('SNOWFLAKE_PASSWORD'),
            role=os.environ.get('SNOWFLAKE_ROLE'),
            warehouse=os.environ.get('SNOWFLAKE_WAREHOUSE'),
            database='INSURANCE_DB'
        )
    
    def _register_default_rules(self):
        """Register default fraud detection rules."""
        self.rules = [
            VelocityRule(name="high_velocity_30d", days=30, threshold=3, score=25),
            VelocityRule(name="high_velocity_90d", days=90, threshold=5, score=20),
            AmountAnomalyRule(name="amount_3std", std_multiplier=3, score=25),
            AmountAnomalyRule(name="amount_p99", percentile=99, score=20),
            TimingRule(name="early_claim", days_from_inception=30, score=20),
            QuickReportRule(name="same_day_report", max_days=1, score=15),
            PatternRule(name="repeated_cause", min_occurrences=3, score=15),
            ClaimToPremiumRule(name="high_claim_ratio", threshold=5.0, score=20),
        ]
    
    def add_rule(self, rule):
        """Add a custom rule to the engine."""
        self.rules.append(rule)
    
    def evaluate_claim(self, claim_data: Dict) -> Dict:
        """Evaluate a single claim against all rules.
        
        Args:
            claim_data: Dictionary containing claim information
            
        Returns:
            Dictionary with fraud score and triggered rules
        """
        total_score = 0
        triggered_rules = []
        
        for rule in self.rules:
            result = rule.evaluate(claim_data, self.conn)
            if result['triggered']:
                total_score += result['score']
                triggered_rules.append({
                    'rule_name': rule.name,
                    'score': result['score'],
                    'details': result.get('details', '')
                })
        
        risk_tier = self._calculate_risk_tier(total_score)
        
        return {
            'claim_id': claim_data.get('claim_id'),
            'total_score': min(total_score, 100),
            'risk_tier': risk_tier,
            'triggered_rules': triggered_rules,
            'evaluated_at': datetime.now().isoformat()
        }
    
    def evaluate_batch(self, claims_df: pd.DataFrame) -> pd.DataFrame:
        """Evaluate multiple claims against all rules.
        
        Args:
            claims_df: DataFrame containing claims data
            
        Returns:
            DataFrame with fraud scores and risk tiers
        """
        results = []
        for _, row in claims_df.iterrows():
            claim_data = row.to_dict()
            result = self.evaluate_claim(claim_data)
            results.append(result)
        
        return pd.DataFrame(results)
    
    def _calculate_risk_tier(self, score: int) -> str:
        """Calculate risk tier based on total score."""
        if score >= 50:
            return 'HIGH'
        elif score >= 25:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def get_high_risk_claims(self, min_score: int = 50) -> pd.DataFrame:
        """Retrieve high-risk claims from the database.
        
        Args:
            min_score: Minimum fraud score threshold
            
        Returns:
            DataFrame of high-risk claims
        """
        query = f"""
        SELECT *
        FROM INSURANCE_DB.RAW_MARTS.MART_FRAUD_FEATURES
        WHERE rule_based_fraud_score >= {min_score}
        ORDER BY rule_based_fraud_score DESC
        """
        cursor = self.conn.cursor()
        cursor.execute(query)
        columns = [desc[0] for desc in cursor.description]
        data = cursor.fetchall()
        cursor.close()
        return pd.DataFrame(data, columns=columns)
    
    def generate_fraud_report(self) -> Dict:
        """Generate a summary fraud report.
        
        Returns:
            Dictionary containing fraud statistics
        """
        query = """
        SELECT 
            fraud_risk_tier,
            COUNT(*) as claim_count,
            AVG(rule_based_fraud_score) as avg_score,
            SUM(incurred_amount) as total_incurred
        FROM INSURANCE_DB.RAW_MARTS.MART_FRAUD_FEATURES
        GROUP BY fraud_risk_tier
        ORDER BY 
            CASE fraud_risk_tier 
                WHEN 'HIGH' THEN 1 
                WHEN 'MEDIUM' THEN 2 
                ELSE 3 
            END
        """
        cursor = self.conn.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        cursor.close()
        
        report = {
            'generated_at': datetime.now().isoformat(),
            'risk_distribution': {}
        }
        
        for row in results:
            tier, count, avg_score, total_incurred = row
            report['risk_distribution'][tier] = {
                'claim_count': count,
                'avg_score': float(avg_score) if avg_score else 0,
                'total_incurred': float(total_incurred) if total_incurred else 0
            }
        
        return report


class FraudRule:
    """Base class for fraud detection rules."""
    
    def __init__(self, name: str, score: int):
        self.name = name
        self.score = score
    
    def evaluate(self, claim_data: Dict, conn) -> Dict:
        """Evaluate the rule against claim data.
        
        Args:
            claim_data: Dictionary containing claim information
            conn: Database connection
            
        Returns:
            Dictionary with 'triggered' boolean and 'score'
        """
        raise NotImplementedError


class VelocityRule(FraudRule):
    """Detect multiple claims within a short time period."""
    
    def __init__(self, name: str, days: int, threshold: int, score: int):
        super().__init__(name, score)
        self.days = days
        self.threshold = threshold
    
    def evaluate(self, claim_data: Dict, conn) -> Dict:
        customer_id = claim_data.get('customer_id')
        loss_date = claim_data.get('loss_date')
        
        if not customer_id or not loss_date:
            return {'triggered': False, 'score': 0}
        
        # Check claims in the time window
        claims_in_window = claim_data.get(f'claims_last_{self.days}_days', 0)
        
        triggered = claims_in_window >= self.threshold
        return {
            'triggered': triggered,
            'score': self.score if triggered else 0,
            'details': f'{claims_in_window} claims in last {self.days} days'
        }


class AmountAnomalyRule(FraudRule):
    """Detect unusually high claim amounts."""
    
    def __init__(self, name: str, score: int, std_multiplier: float = None, percentile: int = None):
        super().__init__(name, score)
        self.std_multiplier = std_multiplier
        self.percentile = percentile
    
    def evaluate(self, claim_data: Dict, conn) -> Dict:
        incurred = claim_data.get('incurred_amount', 0)
        
        if self.std_multiplier:
            triggered = claim_data.get('amount_3_std_above_mean', False)
        elif self.percentile == 99:
            triggered = claim_data.get('amount_above_p99', False)
        else:
            triggered = claim_data.get('amount_above_p95', False)
        
        return {
            'triggered': triggered,
            'score': self.score if triggered else 0,
            'details': f'Incurred amount: {incurred}'
        }


class TimingRule(FraudRule):
    """Detect claims shortly after policy inception."""
    
    def __init__(self, name: str, days_from_inception: int, score: int):
        super().__init__(name, score)
        self.days_from_inception = days_from_inception
    
    def evaluate(self, claim_data: Dict, conn) -> Dict:
        triggered = claim_data.get('claim_within_30_days_of_inception', False)
        days = claim_data.get('days_from_inception', 0)
        
        return {
            'triggered': triggered,
            'score': self.score if triggered else 0,
            'details': f'Claim {days} days after inception'
        }


class QuickReportRule(FraudRule):
    """Detect claims reported very quickly after loss."""
    
    def __init__(self, name: str, max_days: int, score: int):
        super().__init__(name, score)
        self.max_days = max_days
    
    def evaluate(self, claim_data: Dict, conn) -> Dict:
        triggered = claim_data.get('same_day_reporting', False)
        days = claim_data.get('days_to_report', 0)
        
        return {
            'triggered': triggered,
            'score': self.score if triggered else 0,
            'details': f'Reported {days} days after loss'
        }


class PatternRule(FraudRule):
    """Detect repeated claim patterns (same cause)."""
    
    def __init__(self, name: str, min_occurrences: int, score: int):
        super().__init__(name, score)
        self.min_occurrences = min_occurrences
    
    def evaluate(self, claim_data: Dict, conn) -> Dict:
        triggered = claim_data.get('repeated_claim_cause', False)
        
        return {
            'triggered': triggered,
            'score': self.score if triggered else 0,
            'details': 'Repeated claim cause pattern detected'
        }


class ClaimToPremiumRule(FraudRule):
    """Detect claims with high claim-to-premium ratio."""
    
    def __init__(self, name: str, threshold: float, score: int):
        super().__init__(name, score)
        self.threshold = threshold
    
    def evaluate(self, claim_data: Dict, conn) -> Dict:
        ratio = claim_data.get('claim_to_premium_ratio', 0)
        triggered = ratio > self.threshold
        
        return {
            'triggered': triggered,
            'score': self.score if triggered else 0,
            'details': f'Claim-to-premium ratio: {ratio:.2f}'
        }


def run_fraud_detection(output_path: Optional[str] = None) -> pd.DataFrame:
    """Run fraud detection on all claims and optionally save results.
    
    Args:
        output_path: Optional path to save results CSV
        
    Returns:
        DataFrame with fraud detection results
    """
    engine = FraudRuleEngine()
    
    # Get all claims with fraud features
    query = """
    SELECT * FROM INSURANCE_DB.RAW_MARTS.MART_FRAUD_FEATURES
    """
    cursor = engine.conn.cursor()
    cursor.execute(query)
    columns = [desc[0] for desc in cursor.description]
    data = cursor.fetchall()
    cursor.close()
    
    claims_df = pd.DataFrame(data, columns=columns)
    
    # Evaluate all claims
    results_df = engine.evaluate_batch(claims_df)
    
    # Merge with original data
    final_df = claims_df.merge(
        results_df[['claim_id', 'total_score', 'risk_tier', 'triggered_rules']],
        on='claim_id',
        how='left'
    )
    
    if output_path:
        final_df.to_csv(output_path, index=False)
        print(f"Fraud detection results saved to {output_path}")
    
    # Print summary
    report = engine.generate_fraud_report()
    print("\n=== Fraud Detection Report ===")
    print(f"Generated at: {report['generated_at']}")
    for tier, stats in report['risk_distribution'].items():
        print(f"\n{tier} Risk:")
        print(f"  Claims: {stats['claim_count']}")
        print(f"  Avg Score: {stats['avg_score']:.1f}")
        print(f"  Total Incurred: ${stats['total_incurred']:,.2f}")
    
    return final_df


if __name__ == "__main__":
    results = run_fraud_detection()
    print(f"\nProcessed {len(results)} claims")
