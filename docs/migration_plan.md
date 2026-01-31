# Insurance Data Platform - Migration Plan

## Overview

This document outlines the migration plan for consolidating the four insurance repositories into a unified data platform while maintaining backward compatibility and ensuring data persistence.

## Target Folder Structure

```
insurance-data-platform/
├── README.md
├── .env.example
├── docker-compose.yml                    # Unified deployment
├── scripts/
│   ├── deploy.sh                         # Master deployment script
│   ├── setup_snowflake.sql               # Snowflake infrastructure
│   └── load_data.py                      # Data loading utilities
├── data-generator/
│   ├── Simulator.py                      # Continuous generator (from Repo 1)
│   └── batch_generator.py                # Batch generator (from Repo 2)
├── airflow/
│   ├── docker-compose.yml
│   └── dags/
│       └── insurance_elt_pipeline.py
├── dbt/
│   ├── dbt_project.yml
│   ├── profiles.yml
│   ├── packages/
│   │   └── insurance_common/             # Shared package
│   │       ├── macros/
│   │       ├── seeds/
│   │       └── tests/
│   └── models/
│       ├── staging/
│       │   ├── stg_quotes.sql
│       │   ├── stg_policies.sql
│       │   ├── stg_claims.sql
│       │   └── stg_customers.sql         # NEW: from Repo 3
│       ├── core/
│       │   ├── core_policy_claims.sql
│       │   ├── core_policy_snapshot.sql
│       │   └── core_customer_profile.sql # NEW: from Repo 3
│       └── marts/
│           ├── mart_loss_ratio_by_segment.sql
│           ├── mart_customer_risk.sql
│           ├── mart_product_performance.sql
│           ├── mart_customer_claims.sql  # From Repo 3
│           └── mart_policy_summary.sql   # From Repo 3
├── ml/
│   ├── notebooks/
│   │   └── 0_start_here.ipynb            # From Repo 4
│   └── scripts/
│       └── setup.sql                     # From Repo 4
├── infra/
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   └── snowflake/
│       ├── warehouse.tf
│       ├── database.tf
│       ├── roles_users.tf
│       └── stages.tf
└── docs/
    ├── canonical_data_model.md
    ├── duplication_report.md
    ├── conformed_dimensional_model.sql
    └── migration_plan.md
```

## PR Plan for Each Repository

### PR 1: SN_insurance-nosql-pipeline

**Branch:** `devin/insurance-platform-integration`

**Changes:**
1. Add `docker-compose.yml` for Airbyte and data generator
2. Add `Dockerfile.generator` for containerized data generation
3. Add `.env.example` for configuration template
4. Update `requirements.txt` if needed

**Files Added:**
- `docker-compose.yml`
- `Dockerfile.generator`
- `.env.example`

**Testing:**
- Verify docker-compose syntax
- Test data generator container build

### PR 2: snowflake-dbt-airflow-insurance-data-platform

**Branch:** `devin/insurance-platform-integration`

**Changes:**
1. Update `airflow/docker-compose.yml` with full configuration
2. Implement full Airflow DAG with all tasks
3. Implement all dbt staging models
4. Implement all dbt core models
5. Implement all dbt marts models
6. Add source definitions
7. Add shared dbt package
8. Add deployment script
9. Add documentation (canonical model, duplication report, DDL)

**Files Modified:**
- `airflow/docker-compose.yml`
- `airflow/dags/insurance_elt_pipeline.py`
- `dbt/models/staging/stg_quotes.sql`
- `dbt/models/staging/stg_policies.sql`
- `dbt/models/staging/stg_claims.sql`
- `dbt/models/core/core_policy_claims.sql`
- `dbt/models/core/core_policy_snapshot.sql`
- `dbt/models/marts/mart_loss_ratio_by_segment.sql`
- `dbt/models/marts/mart_customer_risk.sql`
- `dbt/models/marts/mart_product_performance.sql`

**Files Added:**
- `dbt/models/staging/sources.yml`
- `dbt/packages/insurance_common/` (entire package)
- `scripts/deploy.sh`
- `docs/canonical_data_model.md`
- `docs/duplication_report.md`
- `docs/conformed_dimensional_model.sql`
- `docs/migration_plan.md`

**Testing:**
- Run `dbt compile` to verify model syntax
- Verify Airflow DAG syntax

### PR 3: SN_dbt-insurance-project

**Branch:** `devin/insurance-platform-integration`

**Changes:**
1. Add `profiles.yml` for Snowflake connection

**Files Added:**
- `profiles.yml`

**Testing:**
- Verify profiles.yml syntax

### PR 4: SN_sfguide-getting-started-with-predicting-insurance-claims-regression-model

**No changes required** - This repository already has the necessary `scripts/setup.sql`.

## Migration Steps

### Phase 1: Preparation (Day 1)

1. **Backup existing data**
   ```bash
   # Export existing Snowflake data
   snowsql -a $SNOWFLAKE_ACCOUNT -u $SNOWFLAKE_USER -f backup_data.sql
   ```

2. **Create feature branches in all repositories**
   ```bash
   git checkout -b devin/insurance-platform-integration
   ```

3. **Review and merge PRs**
   - PR 1: SN_insurance-nosql-pipeline
   - PR 2: snowflake-dbt-airflow-insurance-data-platform
   - PR 3: SN_dbt-insurance-project

### Phase 2: Infrastructure Setup (Day 2)

1. **Run Snowflake setup script**
   ```bash
   snowsql -a $SNOWFLAKE_ACCOUNT -u $SNOWFLAKE_USER \
     -f scripts/setup.sql
   ```

2. **Create additional schemas**
   ```sql
   CREATE SCHEMA IF NOT EXISTS INSURANCE_DB.RAW;
   CREATE SCHEMA IF NOT EXISTS INSURANCE_DB.STAGING;
   CREATE SCHEMA IF NOT EXISTS INSURANCE_DB.CORE;
   CREATE SCHEMA IF NOT EXISTS INSURANCE_DB.MARTS;
   CREATE SCHEMA IF NOT EXISTS INSURANCE_DW;
   ```

3. **Deploy Airflow**
   ```bash
   cd airflow
   docker-compose up -d
   ```

### Phase 3: Data Migration (Day 3)

1. **Generate initial data**
   ```bash
   python python/generate_data.py
   ```

2. **Load raw data to Snowflake**
   ```bash
   ./scripts/deploy.sh 3
   ```

3. **Run dbt transformations**
   ```bash
   cd dbt
   dbt deps
   dbt run
   dbt test
   ```

### Phase 4: Validation (Day 4)

1. **Verify data counts**
   ```sql
   SELECT 'RAW_QUOTES' as table_name, COUNT(*) as row_count FROM RAW.RAW_QUOTES
   UNION ALL
   SELECT 'RAW_POLICIES', COUNT(*) FROM RAW.RAW_POLICIES
   UNION ALL
   SELECT 'RAW_CLAIMS', COUNT(*) FROM RAW.RAW_CLAIMS;
   ```

2. **Verify dbt models**
   ```bash
   dbt test
   ```

3. **Verify loss ratio calculations**
   ```sql
   SELECT * FROM MARTS.MART_LOSS_RATIO_BY_SEGMENT LIMIT 10;
   ```

### Phase 5: Cutover (Day 5)

1. **Update downstream consumers**
   - Update BI tool connections
   - Update API endpoints
   - Update scheduled jobs

2. **Enable Airflow DAG**
   - Access Airflow UI at http://localhost:8080
   - Enable `insurance_elt_pipeline` DAG

3. **Monitor for issues**
   - Check Airflow task logs
   - Monitor Snowflake query history
   - Verify data freshness

## Rollback Plan

### Immediate Rollback (< 1 hour)

If issues are detected within the first hour:

1. **Disable Airflow DAG**
   ```bash
   # Via Airflow UI or CLI
   airflow dags pause insurance_elt_pipeline
   ```

2. **Restore from backup**
   ```bash
   snowsql -a $SNOWFLAKE_ACCOUNT -u $SNOWFLAKE_USER -f restore_data.sql
   ```

3. **Revert code changes**
   ```bash
   git revert HEAD
   git push origin main
   ```

### Extended Rollback (> 1 hour)

If issues are detected after extended operation:

1. **Stop all data pipelines**
   ```bash
   docker-compose down
   ```

2. **Identify affected data**
   ```sql
   SELECT * FROM INFORMATION_SCHEMA.QUERY_HISTORY
   WHERE START_TIME > '2026-01-31 00:00:00'
   ORDER BY START_TIME DESC;
   ```

3. **Restore specific tables**
   ```sql
   CREATE OR REPLACE TABLE RAW.RAW_CLAIMS AS
   SELECT * FROM RAW.RAW_CLAIMS_BACKUP;
   ```

4. **Rebuild dbt models**
   ```bash
   dbt run --full-refresh
   ```

## Data Persistence Strategy

### Snowflake Data Retention

1. **Enable Time Travel**
   ```sql
   ALTER TABLE RAW.RAW_CLAIMS SET DATA_RETENTION_TIME_IN_DAYS = 30;
   ALTER TABLE RAW.RAW_POLICIES SET DATA_RETENTION_TIME_IN_DAYS = 30;
   ALTER TABLE RAW.RAW_QUOTES SET DATA_RETENTION_TIME_IN_DAYS = 30;
   ```

2. **Create backup tables before migration**
   ```sql
   CREATE TABLE RAW.RAW_CLAIMS_BACKUP AS SELECT * FROM RAW.RAW_CLAIMS;
   CREATE TABLE RAW.RAW_POLICIES_BACKUP AS SELECT * FROM RAW.RAW_POLICIES;
   CREATE TABLE RAW.RAW_QUOTES_BACKUP AS SELECT * FROM RAW.RAW_QUOTES;
   ```

### MongoDB Data Retention

1. **Export MongoDB collections**
   ```bash
   mongodump --uri="$MONGODB_URI" --out=/backup/mongodb
   ```

2. **Verify export**
   ```bash
   ls -la /backup/mongodb/insurance/
   ```

### Airflow Metadata

1. **Backup Airflow database**
   ```bash
   docker exec airflow-postgres pg_dump -U airflow airflow > airflow_backup.sql
   ```

## Success Criteria

### Technical Criteria

- [ ] All dbt models compile without errors
- [ ] All dbt tests pass
- [ ] Airflow DAG runs successfully end-to-end
- [ ] Data counts match expected values
- [ ] Loss ratio calculations are accurate

### Business Criteria

- [ ] BI dashboards display correct data
- [ ] No data gaps in time series
- [ ] Customer risk bands are correctly assigned
- [ ] Product performance metrics are accurate

## Timeline

| Day | Phase | Activities |
|-----|-------|------------|
| 1 | Preparation | Backup data, create branches, merge PRs |
| 2 | Infrastructure | Setup Snowflake, deploy Airflow |
| 3 | Data Migration | Generate data, load to Snowflake, run dbt |
| 4 | Validation | Verify data, run tests, check calculations |
| 5 | Cutover | Update consumers, enable DAG, monitor |

## Contacts

| Role | Responsibility |
|------|----------------|
| Data Engineer | Infrastructure setup, dbt development |
| DBA | Snowflake configuration, backup/restore |
| DevOps | Docker deployment, CI/CD |
| Business Analyst | Data validation, acceptance testing |

## Appendix: SQL Scripts

### A. Backup Script

```sql
-- backup_data.sql
CREATE SCHEMA IF NOT EXISTS BACKUP;

CREATE OR REPLACE TABLE BACKUP.RAW_CLAIMS AS SELECT * FROM RAW.RAW_CLAIMS;
CREATE OR REPLACE TABLE BACKUP.RAW_POLICIES AS SELECT * FROM RAW.RAW_POLICIES;
CREATE OR REPLACE TABLE BACKUP.RAW_QUOTES AS SELECT * FROM RAW.RAW_QUOTES;
```

### B. Restore Script

```sql
-- restore_data.sql
CREATE OR REPLACE TABLE RAW.RAW_CLAIMS AS SELECT * FROM BACKUP.RAW_CLAIMS;
CREATE OR REPLACE TABLE RAW.RAW_POLICIES AS SELECT * FROM BACKUP.RAW_POLICIES;
CREATE OR REPLACE TABLE RAW.RAW_QUOTES AS SELECT * FROM BACKUP.RAW_QUOTES;
```

### C. Validation Script

```sql
-- validate_data.sql
SELECT 
    'RAW' as layer,
    (SELECT COUNT(*) FROM RAW.RAW_QUOTES) as quotes,
    (SELECT COUNT(*) FROM RAW.RAW_POLICIES) as policies,
    (SELECT COUNT(*) FROM RAW.RAW_CLAIMS) as claims
UNION ALL
SELECT 
    'STAGING',
    (SELECT COUNT(*) FROM STAGING.STG_QUOTES),
    (SELECT COUNT(*) FROM STAGING.STG_POLICIES),
    (SELECT COUNT(*) FROM STAGING.STG_CLAIMS)
UNION ALL
SELECT 
    'MARTS',
    NULL,
    NULL,
    (SELECT COUNT(*) FROM MARTS.MART_LOSS_RATIO_BY_SEGMENT);
```
