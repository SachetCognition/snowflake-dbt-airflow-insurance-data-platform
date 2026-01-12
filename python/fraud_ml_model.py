"""
ML-based fraud detection module for insurance claims.

This module implements machine learning algorithms for fraud detection:
1. Isolation Forest for anomaly detection
2. Feature engineering for ML models
3. Model training and inference
4. Ensemble scoring combining multiple models
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import pickle
import warnings
warnings.filterwarnings('ignore')

try:
    from sklearn.ensemble import IsolationForest, RandomForestClassifier
    from sklearn.preprocessing import StandardScaler, LabelEncoder
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import classification_report, roc_auc_score, precision_recall_curve
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("Warning: scikit-learn not installed. ML features will be limited.")

import snowflake.connector
from dotenv import load_dotenv

load_dotenv()


class FraudFeatureEngineer:
    """Feature engineering for fraud detection ML models."""
    
    # Features to use for ML models
    NUMERIC_FEATURES = [
        'incurred_amount',
        'paid_amount',
        'reserve_amount',
        'risk_score',
        'premium_written',
        'claims_last_30_days',
        'claims_last_90_days',
        'cumulative_policy_claims',
        'days_to_report',
        'days_from_inception',
        'customer_total_claims',
        'customer_total_claim_amount',
        'claim_to_premium_ratio',
        'rule_based_fraud_score',
    ]
    
    CATEGORICAL_FEATURES = [
        'product',
        'channel',
        'claim_cause',
        'coverage_type',
        'claim_status',
        'risk_band',
    ]
    
    BOOLEAN_FEATURES = [
        'claim_within_30_days_of_inception',
        'same_day_reporting',
        'amount_3_std_above_mean',
        'amount_above_p95',
        'amount_above_p99',
        'amount_anomaly_for_product',
        'repeated_claim_cause',
    ]
    
    def __init__(self):
        self.scaler = StandardScaler() if SKLEARN_AVAILABLE else None
        self.label_encoders = {}
        self.fitted = False
    
    def fit_transform(self, df: pd.DataFrame) -> np.ndarray:
        """Fit the feature engineer and transform data.
        
        Args:
            df: DataFrame with raw features
            
        Returns:
            Numpy array of engineered features
        """
        features = self._extract_features(df)
        
        if SKLEARN_AVAILABLE:
            # Fit and transform numeric features
            numeric_cols = [c for c in self.NUMERIC_FEATURES if c in features.columns]
            features[numeric_cols] = self.scaler.fit_transform(features[numeric_cols].fillna(0))
            
            # Fit and transform categorical features
            for col in self.CATEGORICAL_FEATURES:
                if col in features.columns:
                    self.label_encoders[col] = LabelEncoder()
                    features[col] = self.label_encoders[col].fit_transform(
                        features[col].fillna('UNKNOWN').astype(str)
                    )
        
        self.fitted = True
        return features.values
    
    def transform(self, df: pd.DataFrame) -> np.ndarray:
        """Transform data using fitted feature engineer.
        
        Args:
            df: DataFrame with raw features
            
        Returns:
            Numpy array of engineered features
        """
        if not self.fitted:
            raise ValueError("Feature engineer not fitted. Call fit_transform first.")
        
        features = self._extract_features(df)
        
        if SKLEARN_AVAILABLE:
            # Transform numeric features
            numeric_cols = [c for c in self.NUMERIC_FEATURES if c in features.columns]
            features[numeric_cols] = self.scaler.transform(features[numeric_cols].fillna(0))
            
            # Transform categorical features
            for col in self.CATEGORICAL_FEATURES:
                if col in features.columns and col in self.label_encoders:
                    # Handle unseen categories
                    features[col] = features[col].fillna('UNKNOWN').astype(str)
                    features[col] = features[col].apply(
                        lambda x: self.label_encoders[col].transform([x])[0] 
                        if x in self.label_encoders[col].classes_ 
                        else -1
                    )
        
        return features.values
    
    def _extract_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract and prepare features from raw data."""
        features = pd.DataFrame()
        
        # Numeric features
        for col in self.NUMERIC_FEATURES:
            if col in df.columns:
                features[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # Categorical features
        for col in self.CATEGORICAL_FEATURES:
            if col in df.columns:
                features[col] = df[col].fillna('UNKNOWN')
        
        # Boolean features (convert to int)
        for col in self.BOOLEAN_FEATURES:
            if col in df.columns:
                features[col] = df[col].astype(int) if df[col].dtype == bool else df[col].fillna(0)
        
        # Derived features
        if 'incurred_amount' in df.columns and 'premium_written' in df.columns:
            features['claim_severity_ratio'] = (
                df['incurred_amount'] / df['premium_written'].replace(0, 1)
            ).fillna(0)
        
        if 'claims_last_30_days' in df.columns and 'claims_last_90_days' in df.columns:
            features['velocity_acceleration'] = (
                df['claims_last_30_days'] / df['claims_last_90_days'].replace(0, 1)
            ).fillna(0)
        
        return features
    
    def get_feature_names(self) -> List[str]:
        """Get list of feature names."""
        return (
            self.NUMERIC_FEATURES + 
            self.CATEGORICAL_FEATURES + 
            self.BOOLEAN_FEATURES + 
            ['claim_severity_ratio', 'velocity_acceleration']
        )


class IsolationForestDetector:
    """Isolation Forest based anomaly detection for fraud."""
    
    def __init__(self, contamination: float = 0.05, n_estimators: int = 100, random_state: int = 42):
        """Initialize Isolation Forest detector.
        
        Args:
            contamination: Expected proportion of outliers (fraud rate)
            n_estimators: Number of trees in the forest
            random_state: Random seed for reproducibility
        """
        if not SKLEARN_AVAILABLE:
            raise ImportError("scikit-learn is required for IsolationForestDetector")
        
        self.model = IsolationForest(
            contamination=contamination,
            n_estimators=n_estimators,
            random_state=random_state,
            n_jobs=-1
        )
        self.feature_engineer = FraudFeatureEngineer()
        self.fitted = False
    
    def fit(self, df: pd.DataFrame) -> 'IsolationForestDetector':
        """Fit the Isolation Forest model.
        
        Args:
            df: DataFrame with fraud features
            
        Returns:
            Self for method chaining
        """
        X = self.feature_engineer.fit_transform(df)
        self.model.fit(X)
        self.fitted = True
        return self
    
    def predict(self, df: pd.DataFrame) -> np.ndarray:
        """Predict anomaly labels.
        
        Args:
            df: DataFrame with fraud features
            
        Returns:
            Array of predictions (-1 for anomaly, 1 for normal)
        """
        if not self.fitted:
            raise ValueError("Model not fitted. Call fit first.")
        
        X = self.feature_engineer.transform(df)
        return self.model.predict(X)
    
    def score_samples(self, df: pd.DataFrame) -> np.ndarray:
        """Get anomaly scores for samples.
        
        Args:
            df: DataFrame with fraud features
            
        Returns:
            Array of anomaly scores (lower = more anomalous)
        """
        if not self.fitted:
            raise ValueError("Model not fitted. Call fit first.")
        
        X = self.feature_engineer.transform(df)
        return self.model.score_samples(X)
    
    def get_fraud_probability(self, df: pd.DataFrame) -> np.ndarray:
        """Convert anomaly scores to fraud probability (0-1).
        
        Args:
            df: DataFrame with fraud features
            
        Returns:
            Array of fraud probabilities
        """
        scores = self.score_samples(df)
        # Convert scores to probabilities (more negative = higher fraud probability)
        # Normalize to 0-1 range
        min_score = scores.min()
        max_score = scores.max()
        if max_score == min_score:
            return np.zeros(len(scores))
        
        # Invert so higher = more fraudulent
        probs = (max_score - scores) / (max_score - min_score)
        return probs


class SupervisedFraudClassifier:
    """Supervised fraud classifier using Random Forest."""
    
    def __init__(self, n_estimators: int = 100, random_state: int = 42):
        """Initialize supervised classifier.
        
        Args:
            n_estimators: Number of trees
            random_state: Random seed
        """
        if not SKLEARN_AVAILABLE:
            raise ImportError("scikit-learn is required for SupervisedFraudClassifier")
        
        self.model = RandomForestClassifier(
            n_estimators=n_estimators,
            random_state=random_state,
            class_weight='balanced',  # Handle imbalanced classes
            n_jobs=-1
        )
        self.feature_engineer = FraudFeatureEngineer()
        self.fitted = False
    
    def fit(self, df: pd.DataFrame, labels: np.ndarray) -> 'SupervisedFraudClassifier':
        """Fit the classifier.
        
        Args:
            df: DataFrame with fraud features
            labels: Array of fraud labels (0/1)
            
        Returns:
            Self for method chaining
        """
        X = self.feature_engineer.fit_transform(df)
        self.model.fit(X, labels)
        self.fitted = True
        return self
    
    def predict(self, df: pd.DataFrame) -> np.ndarray:
        """Predict fraud labels.
        
        Args:
            df: DataFrame with fraud features
            
        Returns:
            Array of predictions (0 or 1)
        """
        if not self.fitted:
            raise ValueError("Model not fitted. Call fit first.")
        
        X = self.feature_engineer.transform(df)
        return self.model.predict(X)
    
    def predict_proba(self, df: pd.DataFrame) -> np.ndarray:
        """Get fraud probabilities.
        
        Args:
            df: DataFrame with fraud features
            
        Returns:
            Array of fraud probabilities
        """
        if not self.fitted:
            raise ValueError("Model not fitted. Call fit first.")
        
        X = self.feature_engineer.transform(df)
        return self.model.predict_proba(X)[:, 1]
    
    def get_feature_importance(self) -> pd.DataFrame:
        """Get feature importance scores.
        
        Returns:
            DataFrame with feature names and importance scores
        """
        if not self.fitted:
            raise ValueError("Model not fitted. Call fit first.")
        
        importance = self.model.feature_importances_
        feature_names = self.feature_engineer.get_feature_names()
        
        # Truncate to match actual features used
        n_features = len(importance)
        feature_names = feature_names[:n_features]
        
        return pd.DataFrame({
            'feature': feature_names,
            'importance': importance
        }).sort_values('importance', ascending=False)


class EnsembleFraudDetector:
    """Ensemble fraud detector combining multiple models."""
    
    def __init__(self):
        """Initialize ensemble detector."""
        self.isolation_forest = None
        self.supervised_classifier = None
        self.conn = None
    
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
    
    def load_training_data(self) -> Tuple[pd.DataFrame, Optional[np.ndarray]]:
        """Load training data from Snowflake.
        
        Returns:
            Tuple of (features DataFrame, labels array if available)
        """
        self.conn = self._create_connection()
        
        query = """
        SELECT * FROM INSURANCE_DB.RAW_MARTS.MART_FRAUD_FEATURES
        """
        cursor = self.conn.cursor()
        cursor.execute(query)
        columns = [desc[0].lower() for desc in cursor.description]
        data = cursor.fetchall()
        cursor.close()
        
        df = pd.DataFrame(data, columns=columns)
        
        # Check if we have ground truth labels
        labels = None
        if 'is_fraud' in df.columns:
            labels = df['is_fraud'].astype(int).values
        
        return df, labels
    
    def train(self, use_supervised: bool = True) -> 'EnsembleFraudDetector':
        """Train the ensemble models.
        
        Args:
            use_supervised: Whether to train supervised model (requires labels)
            
        Returns:
            Self for method chaining
        """
        if not SKLEARN_AVAILABLE:
            print("Warning: scikit-learn not available. Skipping ML training.")
            return self
        
        df, labels = self.load_training_data()
        
        print(f"Training on {len(df)} claims...")
        
        # Train Isolation Forest (unsupervised)
        print("Training Isolation Forest...")
        self.isolation_forest = IsolationForestDetector(contamination=0.05)
        self.isolation_forest.fit(df)
        
        # Train supervised classifier if labels available
        if use_supervised and labels is not None:
            print("Training supervised classifier...")
            self.supervised_classifier = SupervisedFraudClassifier()
            self.supervised_classifier.fit(df, labels)
            
            # Evaluate on training data
            predictions = self.supervised_classifier.predict(df)
            print("\nTraining Performance:")
            print(classification_report(labels, predictions, target_names=['Legitimate', 'Fraud']))
        
        return self
    
    def predict(self, df: pd.DataFrame) -> pd.DataFrame:
        """Get ensemble predictions.
        
        Args:
            df: DataFrame with fraud features
            
        Returns:
            DataFrame with predictions from all models
        """
        results = pd.DataFrame()
        results['claim_id'] = df['claim_id'] if 'claim_id' in df.columns else range(len(df))
        
        if self.isolation_forest:
            results['isolation_forest_score'] = self.isolation_forest.get_fraud_probability(df)
            results['isolation_forest_prediction'] = (
                self.isolation_forest.predict(df) == -1
            ).astype(int)
        
        if self.supervised_classifier:
            results['supervised_score'] = self.supervised_classifier.predict_proba(df)
            results['supervised_prediction'] = self.supervised_classifier.predict(df)
        
        # Ensemble score (average of available models)
        score_cols = [c for c in results.columns if c.endswith('_score')]
        if score_cols:
            results['ensemble_score'] = results[score_cols].mean(axis=1)
            results['ensemble_risk_tier'] = pd.cut(
                results['ensemble_score'],
                bins=[0, 0.25, 0.5, 1.0],
                labels=['LOW', 'MEDIUM', 'HIGH']
            )
        
        return results
    
    def save_model(self, path: str):
        """Save trained models to disk.
        
        Args:
            path: Directory path to save models
        """
        os.makedirs(path, exist_ok=True)
        
        if self.isolation_forest:
            with open(os.path.join(path, 'isolation_forest.pkl'), 'wb') as f:
                pickle.dump(self.isolation_forest, f)
        
        if self.supervised_classifier:
            with open(os.path.join(path, 'supervised_classifier.pkl'), 'wb') as f:
                pickle.dump(self.supervised_classifier, f)
        
        print(f"Models saved to {path}")
    
    def load_model(self, path: str):
        """Load trained models from disk.
        
        Args:
            path: Directory path containing saved models
        """
        iso_path = os.path.join(path, 'isolation_forest.pkl')
        if os.path.exists(iso_path):
            with open(iso_path, 'rb') as f:
                self.isolation_forest = pickle.load(f)
        
        sup_path = os.path.join(path, 'supervised_classifier.pkl')
        if os.path.exists(sup_path):
            with open(sup_path, 'rb') as f:
                self.supervised_classifier = pickle.load(f)
        
        print(f"Models loaded from {path}")


def run_ml_fraud_detection(output_path: Optional[str] = None) -> pd.DataFrame:
    """Run ML-based fraud detection pipeline.
    
    Args:
        output_path: Optional path to save results
        
    Returns:
        DataFrame with ML fraud predictions
    """
    if not SKLEARN_AVAILABLE:
        print("Error: scikit-learn is required for ML fraud detection")
        print("Install with: pip install scikit-learn")
        return pd.DataFrame()
    
    # Initialize and train ensemble
    ensemble = EnsembleFraudDetector()
    ensemble.train(use_supervised=True)
    
    # Load data for prediction
    df, labels = ensemble.load_training_data()
    
    # Get predictions
    results = ensemble.predict(df)
    
    # Merge with original data
    final_df = df.merge(results, on='claim_id', how='left')
    
    if output_path:
        final_df.to_csv(output_path, index=False)
        print(f"ML fraud detection results saved to {output_path}")
    
    # Print summary
    print("\n=== ML Fraud Detection Summary ===")
    if 'ensemble_risk_tier' in results.columns:
        print("\nRisk Distribution:")
        print(results['ensemble_risk_tier'].value_counts())
    
    if 'ensemble_score' in results.columns:
        print(f"\nAverage Ensemble Score: {results['ensemble_score'].mean():.3f}")
        print(f"Max Ensemble Score: {results['ensemble_score'].max():.3f}")
    
    # Feature importance if supervised model trained
    if ensemble.supervised_classifier:
        print("\nTop 10 Important Features:")
        importance = ensemble.supervised_classifier.get_feature_importance()
        print(importance.head(10).to_string(index=False))
    
    return final_df


if __name__ == "__main__":
    results = run_ml_fraud_detection()
    print(f"\nProcessed {len(results)} claims with ML models")
