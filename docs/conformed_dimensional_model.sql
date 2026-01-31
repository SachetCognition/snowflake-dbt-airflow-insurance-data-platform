-- ============================================================================
-- Conformed Dimensional Model for Insurance Data Platform
-- ============================================================================
-- This DDL creates the target schema for the unified insurance data warehouse
-- following Kimball dimensional modeling principles.
-- ============================================================================

-- ============================================================================
-- SCHEMA CREATION
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS INSURANCE_DW;
USE SCHEMA INSURANCE_DW;

-- ============================================================================
-- DIMENSION TABLES
-- ============================================================================

-- ----------------------------------------------------------------------------
-- dim_date: Calendar dimension for time-based analysis
-- ----------------------------------------------------------------------------
CREATE OR REPLACE TABLE dim_date (
    date_key INTEGER NOT NULL PRIMARY KEY,
    full_date DATE NOT NULL,
    day_of_week INTEGER,
    day_name VARCHAR(10),
    day_of_month INTEGER,
    day_of_year INTEGER,
    week_of_year INTEGER,
    month_number INTEGER,
    month_name VARCHAR(10),
    quarter_number INTEGER,
    quarter_name VARCHAR(10),
    year_number INTEGER,
    is_weekend BOOLEAN,
    is_holiday BOOLEAN,
    fiscal_year INTEGER,
    fiscal_quarter INTEGER
);

-- ----------------------------------------------------------------------------
-- dim_customer: Customer/Policyholder dimension (SCD Type 2)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE TABLE dim_customer (
    customer_key INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    customer_name VARCHAR(200),
    age INTEGER,
    gender VARCHAR(20),
    marital_status VARCHAR(50),
    occupation VARCHAR(100),
    income_level VARCHAR(50),
    education_level VARCHAR(100),
    location VARCHAR(200),
    state VARCHAR(50),
    region VARCHAR(100),
    geographic_info VARCHAR(500),
    segmentation_group VARCHAR(100),
    credit_score INTEGER,
    risk_profile VARCHAR(50),
    driving_record VARCHAR(500),
    preferred_communication_channel VARCHAR(50),
    preferred_contact_time VARCHAR(50),
    preferred_language VARCHAR(50),
    -- SCD Type 2 columns
    effective_date DATE NOT NULL,
    end_date DATE,
    is_current BOOLEAN NOT NULL DEFAULT TRUE,
    -- Audit columns
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- ----------------------------------------------------------------------------
-- dim_policy: Policy dimension (SCD Type 2)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE TABLE dim_policy (
    policy_key INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    policy_id INTEGER NOT NULL,
    policy_number VARCHAR(50),
    quote_id INTEGER,
    quote_number VARCHAR(50),
    customer_id INTEGER NOT NULL,
    product VARCHAR(50) NOT NULL,
    product_category VARCHAR(50),
    inception_date DATE,
    expiry_date DATE,
    policy_term_days INTEGER,
    premium_written DECIMAL(18,2),
    premium_quoted DECIMAL(18,2),
    premium_adjustment DECIMAL(18,2),
    payment_frequency VARCHAR(20),
    policy_status VARCHAR(50),
    policy_status_detail VARCHAR(100),
    channel VARCHAR(50),
    risk_score DECIMAL(5,4),
    coverage_amount DECIMAL(18,2),
    deductible DECIMAL(18,2),
    -- SCD Type 2 columns
    effective_date DATE NOT NULL,
    end_date DATE,
    is_current BOOLEAN NOT NULL DEFAULT TRUE,
    version_number INTEGER DEFAULT 1,
    -- Audit columns
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- ----------------------------------------------------------------------------
-- dim_coverage: Coverage type dimension (SCD Type 1)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE TABLE dim_coverage (
    coverage_key INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    coverage_type VARCHAR(100) NOT NULL,
    coverage_category VARCHAR(50),
    coverage_description VARCHAR(500),
    is_comprehensive BOOLEAN,
    is_third_party BOOLEAN,
    -- Audit columns
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- ----------------------------------------------------------------------------
-- dim_claim_cause: Claim cause/type dimension (SCD Type 1)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE TABLE dim_claim_cause (
    claim_cause_key INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    claim_cause VARCHAR(100) NOT NULL,
    claim_cause_category VARCHAR(50),
    claim_cause_description VARCHAR(500),
    typical_severity VARCHAR(20),
    -- Audit columns
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- ----------------------------------------------------------------------------
-- dim_claim_status: Claim status dimension (SCD Type 1)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE TABLE dim_claim_status (
    claim_status_key INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    claim_status VARCHAR(50) NOT NULL,
    claim_status_category VARCHAR(50),
    claim_status_description VARCHAR(500),
    is_open BOOLEAN,
    is_closed BOOLEAN,
    is_denied BOOLEAN,
    -- Audit columns
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- ----------------------------------------------------------------------------
-- dim_adjuster: Claims adjuster dimension (SCD Type 2) - NEW ENTITY
-- ----------------------------------------------------------------------------
CREATE OR REPLACE TABLE dim_adjuster (
    adjuster_key INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    adjuster_id INTEGER NOT NULL,
    adjuster_name VARCHAR(200),
    adjuster_type VARCHAR(50),
    specialization VARCHAR(100),
    license_number VARCHAR(50),
    hire_date DATE,
    department VARCHAR(100),
    region VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    -- SCD Type 2 columns
    effective_date DATE NOT NULL,
    end_date DATE,
    is_current BOOLEAN NOT NULL DEFAULT TRUE,
    -- Audit columns
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- ----------------------------------------------------------------------------
-- dim_provider: Service provider/repairer dimension (SCD Type 2) - NEW ENTITY
-- ----------------------------------------------------------------------------
CREATE OR REPLACE TABLE dim_provider (
    provider_key INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    provider_id INTEGER NOT NULL,
    provider_name VARCHAR(200),
    provider_type VARCHAR(50),
    specialization VARCHAR(100),
    address VARCHAR(500),
    city VARCHAR(100),
    state VARCHAR(50),
    postal_code VARCHAR(20),
    phone VARCHAR(50),
    email VARCHAR(200),
    is_preferred BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    rating DECIMAL(3,2),
    -- SCD Type 2 columns
    effective_date DATE NOT NULL,
    end_date DATE,
    is_current BOOLEAN NOT NULL DEFAULT TRUE,
    -- Audit columns
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- ----------------------------------------------------------------------------
-- dim_vehicle: Vehicle dimension (for motor insurance) - NEW ENTITY
-- ----------------------------------------------------------------------------
CREATE OR REPLACE TABLE dim_vehicle (
    vehicle_key INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    vehicle_id INTEGER,
    policy_id INTEGER,
    vehicle_brand VARCHAR(100),
    vehicle_model VARCHAR(100),
    vehicle_power VARCHAR(50),
    vehicle_age INTEGER,
    vehicle_year INTEGER,
    vehicle_gas VARCHAR(50),
    vin VARCHAR(50),
    license_plate VARCHAR(20),
    -- Audit columns
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- ============================================================================
-- FACT TABLES
-- ============================================================================

-- ----------------------------------------------------------------------------
-- fact_claims: Claim header fact table (grain: one row per claim)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE TABLE fact_claims (
    claim_key INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    -- Degenerate dimensions
    claim_id INTEGER NOT NULL,
    claim_number VARCHAR(50),
    -- Foreign keys to dimensions
    policy_key INTEGER REFERENCES dim_policy(policy_key),
    customer_key INTEGER REFERENCES dim_customer(customer_key),
    coverage_key INTEGER REFERENCES dim_coverage(coverage_key),
    claim_cause_key INTEGER REFERENCES dim_claim_cause(claim_cause_key),
    claim_status_key INTEGER REFERENCES dim_claim_status(claim_status_key),
    adjuster_key INTEGER REFERENCES dim_adjuster(adjuster_key),
    provider_key INTEGER REFERENCES dim_provider(provider_key),
    -- Date keys
    loss_date_key INTEGER REFERENCES dim_date(date_key),
    report_date_key INTEGER REFERENCES dim_date(date_key),
    settlement_date_key INTEGER REFERENCES dim_date(date_key),
    -- Measures
    incurred_amount DECIMAL(18,2),
    paid_amount DECIMAL(18,2),
    reserve_amount DECIMAL(18,2),
    deductible_amount DECIMAL(18,2),
    subrogation_amount DECIMAL(18,2),
    salvage_amount DECIMAL(18,2),
    -- Calculated measures
    days_to_report INTEGER,
    days_to_settle INTEGER,
    -- Flags
    is_fraud BOOLEAN DEFAULT FALSE,
    is_litigated BOOLEAN DEFAULT FALSE,
    is_subrogated BOOLEAN DEFAULT FALSE,
    -- Source tracking
    source_system VARCHAR(50),
    source_claim_id VARCHAR(100),
    -- Audit columns
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- ----------------------------------------------------------------------------
-- fact_claim_transactions: Claim transaction fact table (grain: one row per transaction)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE TABLE fact_claim_transactions (
    transaction_key INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    -- Degenerate dimensions
    transaction_id INTEGER NOT NULL,
    claim_id INTEGER NOT NULL,
    -- Foreign keys
    claim_key INTEGER REFERENCES fact_claims(claim_key),
    policy_key INTEGER REFERENCES dim_policy(policy_key),
    customer_key INTEGER REFERENCES dim_customer(customer_key),
    provider_key INTEGER REFERENCES dim_provider(provider_key),
    -- Date keys
    transaction_date_key INTEGER REFERENCES dim_date(date_key),
    -- Transaction details
    transaction_type VARCHAR(50),
    transaction_category VARCHAR(50),
    -- Measures
    transaction_amount DECIMAL(18,2),
    running_paid_total DECIMAL(18,2),
    running_reserve_total DECIMAL(18,2),
    -- Audit columns
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- ----------------------------------------------------------------------------
-- fact_quotes: Quote fact table (grain: one row per quote)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE TABLE fact_quotes (
    quote_key INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    -- Degenerate dimensions
    quote_id INTEGER NOT NULL,
    quote_number VARCHAR(50),
    -- Foreign keys
    customer_key INTEGER REFERENCES dim_customer(customer_key),
    -- Date keys
    quote_date_key INTEGER REFERENCES dim_date(date_key),
    -- Quote details
    product VARCHAR(50),
    channel VARCHAR(50),
    quote_status VARCHAR(50),
    -- Measures
    risk_score DECIMAL(5,4),
    premium_quoted DECIMAL(18,2),
    -- Conversion tracking
    converted_to_policy BOOLEAN DEFAULT FALSE,
    policy_key INTEGER REFERENCES dim_policy(policy_key),
    -- Audit columns
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- ----------------------------------------------------------------------------
-- fact_policy_premium: Policy premium fact table (grain: one row per policy per month)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE TABLE fact_policy_premium (
    premium_key INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    -- Foreign keys
    policy_key INTEGER REFERENCES dim_policy(policy_key),
    customer_key INTEGER REFERENCES dim_customer(customer_key),
    -- Date keys
    period_date_key INTEGER REFERENCES dim_date(date_key),
    -- Measures
    written_premium DECIMAL(18,2),
    earned_premium DECIMAL(18,2),
    unearned_premium DECIMAL(18,2),
    -- Audit columns
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- ============================================================================
-- AGGREGATE/METRICS TABLES
-- ============================================================================

-- ----------------------------------------------------------------------------
-- agg_loss_ratio_monthly: Pre-aggregated loss ratio by segment
-- ----------------------------------------------------------------------------
CREATE OR REPLACE TABLE agg_loss_ratio_monthly (
    agg_key INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    -- Dimensions
    year_month DATE NOT NULL,
    product VARCHAR(50),
    channel VARCHAR(50),
    region VARCHAR(100),
    -- Measures
    policy_count INTEGER,
    earned_premium DECIMAL(18,2),
    claim_count INTEGER,
    incurred_claims DECIMAL(18,2),
    paid_claims DECIMAL(18,2),
    reserve_amount DECIMAL(18,2),
    -- Calculated metrics
    loss_ratio DECIMAL(8,4),
    claim_frequency DECIMAL(8,4),
    average_severity DECIMAL(18,2),
    -- Audit columns
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- ----------------------------------------------------------------------------
-- agg_customer_risk: Pre-aggregated customer risk metrics
-- ----------------------------------------------------------------------------
CREATE OR REPLACE TABLE agg_customer_risk (
    agg_key INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    -- Dimensions
    customer_key INTEGER REFERENCES dim_customer(customer_key),
    as_of_date DATE NOT NULL,
    -- Measures
    total_policies INTEGER,
    active_policies INTEGER,
    total_premium_written DECIMAL(18,2),
    avg_risk_score DECIMAL(5,4),
    total_claims INTEGER,
    total_incurred DECIMAL(18,2),
    total_paid DECIMAL(18,2),
    -- Calculated metrics
    claim_frequency DECIMAL(8,4),
    avg_claim_severity DECIMAL(18,2),
    customer_loss_ratio DECIMAL(8,4),
    risk_band VARCHAR(20),
    -- Audit columns
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- ============================================================================
-- SEED DATA FOR LOOKUP DIMENSIONS
-- ============================================================================

-- Seed dim_claim_status
INSERT INTO dim_claim_status (claim_status, claim_status_category, claim_status_description, is_open, is_closed, is_denied)
VALUES
    ('OPEN', 'Active', 'Claim is open and being processed', TRUE, FALSE, FALSE),
    ('CLOSED', 'Resolved', 'Claim has been settled and closed', FALSE, TRUE, FALSE),
    ('REJECTED', 'Resolved', 'Claim has been denied', FALSE, FALSE, TRUE),
    ('REOPENED', 'Active', 'Previously closed claim has been reopened', TRUE, FALSE, FALSE),
    ('UNDER_REVIEW', 'Active', 'Claim is under review', TRUE, FALSE, FALSE),
    ('SUBROGATION', 'Active', 'Claim is in subrogation process', TRUE, FALSE, FALSE),
    ('LITIGATION', 'Active', 'Claim is in litigation', TRUE, FALSE, FALSE);

-- Seed dim_claim_cause
INSERT INTO dim_claim_cause (claim_cause, claim_cause_category, claim_cause_description, typical_severity)
VALUES
    ('Collision', 'Accident', 'Vehicle collision with another vehicle or object', 'MEDIUM'),
    ('Theft', 'Crime', 'Vehicle or property theft', 'HIGH'),
    ('Fire', 'Disaster', 'Fire damage to vehicle or property', 'HIGH'),
    ('Weather', 'Natural', 'Weather-related damage (hail, flood, wind)', 'MEDIUM'),
    ('Vandalism', 'Crime', 'Intentional damage to property', 'LOW'),
    ('Other', 'Miscellaneous', 'Other causes not categorized', 'LOW'),
    ('Accident', 'Accident', 'General accident (non-collision)', 'MEDIUM');

-- Seed dim_coverage
INSERT INTO dim_coverage (coverage_type, coverage_category, coverage_description, is_comprehensive, is_third_party)
VALUES
    ('Third Party', 'Liability', 'Coverage for damage to third parties', FALSE, TRUE),
    ('Comprehensive', 'Full', 'Full coverage including own damage', TRUE, FALSE),
    ('Third Party Fire and Theft', 'Partial', 'Third party plus fire and theft coverage', FALSE, TRUE),
    ('Collision', 'Partial', 'Coverage for collision damage only', FALSE, FALSE),
    ('Personal Injury', 'Liability', 'Coverage for personal injury claims', FALSE, TRUE);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

-- Fact table indexes
CREATE INDEX IF NOT EXISTS idx_fact_claims_policy ON fact_claims(policy_key);
CREATE INDEX IF NOT EXISTS idx_fact_claims_customer ON fact_claims(customer_key);
CREATE INDEX IF NOT EXISTS idx_fact_claims_loss_date ON fact_claims(loss_date_key);
CREATE INDEX IF NOT EXISTS idx_fact_claims_status ON fact_claims(claim_status_key);

CREATE INDEX IF NOT EXISTS idx_fact_transactions_claim ON fact_claim_transactions(claim_key);
CREATE INDEX IF NOT EXISTS idx_fact_transactions_date ON fact_claim_transactions(transaction_date_key);

CREATE INDEX IF NOT EXISTS idx_fact_quotes_customer ON fact_quotes(customer_key);
CREATE INDEX IF NOT EXISTS idx_fact_quotes_date ON fact_quotes(quote_date_key);

-- Dimension table indexes
CREATE INDEX IF NOT EXISTS idx_dim_customer_id ON dim_customer(customer_id);
CREATE INDEX IF NOT EXISTS idx_dim_customer_current ON dim_customer(is_current);

CREATE INDEX IF NOT EXISTS idx_dim_policy_id ON dim_policy(policy_id);
CREATE INDEX IF NOT EXISTS idx_dim_policy_customer ON dim_policy(customer_id);
CREATE INDEX IF NOT EXISTS idx_dim_policy_current ON dim_policy(is_current);

-- ============================================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================================

-- Current customer view (latest version only)
CREATE OR REPLACE VIEW v_current_customers AS
SELECT * FROM dim_customer WHERE is_current = TRUE;

-- Current policy view (latest version only)
CREATE OR REPLACE VIEW v_current_policies AS
SELECT * FROM dim_policy WHERE is_current = TRUE;

-- Claims with all dimensions joined
CREATE OR REPLACE VIEW v_claims_detail AS
SELECT
    fc.claim_id,
    fc.claim_number,
    dc.customer_name,
    dp.policy_number,
    dp.product,
    dcc.claim_cause,
    dcov.coverage_type,
    dcs.claim_status,
    dd_loss.full_date AS loss_date,
    dd_report.full_date AS report_date,
    dd_settle.full_date AS settlement_date,
    fc.incurred_amount,
    fc.paid_amount,
    fc.reserve_amount,
    fc.days_to_report,
    fc.days_to_settle,
    fc.is_fraud
FROM fact_claims fc
LEFT JOIN dim_customer dc ON fc.customer_key = dc.customer_key
LEFT JOIN dim_policy dp ON fc.policy_key = dp.policy_key
LEFT JOIN dim_claim_cause dcc ON fc.claim_cause_key = dcc.claim_cause_key
LEFT JOIN dim_coverage dcov ON fc.coverage_key = dcov.coverage_key
LEFT JOIN dim_claim_status dcs ON fc.claim_status_key = dcs.claim_status_key
LEFT JOIN dim_date dd_loss ON fc.loss_date_key = dd_loss.date_key
LEFT JOIN dim_date dd_report ON fc.report_date_key = dd_report.date_key
LEFT JOIN dim_date dd_settle ON fc.settlement_date_key = dd_settle.date_key;

-- Loss ratio summary view
CREATE OR REPLACE VIEW v_loss_ratio_summary AS
SELECT
    year_month,
    product,
    channel,
    policy_count,
    earned_premium,
    claim_count,
    incurred_claims,
    loss_ratio,
    claim_frequency,
    average_severity
FROM agg_loss_ratio_monthly
ORDER BY year_month DESC, product, channel;
