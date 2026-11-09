# PL Capital AI Portfolio Analytics Agent

**AI Engineering Take-Home Assessment — Complete Multi-Phase Deliverable**  
- **Phase 1: Project Architecture, SQLite Database Foundation & Ingestion Engine**  
- **Phase 2: Intelligent Natural Language to SQL Query Engine**  
- **Phase 3: Portfolio Sector Exposure Calculator (Equities Only, Bonds Excluded)**  
- **Phase 4: Gemini-Powered Portfolio AI Agent & Tool Orchestration**  
- **Phase 5: Agent Evaluator, Ground Truth Validation & Benchmark Reporting**  
- **Phase 6: Professional Streamlit Dashboard & Final Integration**  
- **Phase 7: Final Submission Audit, Hardening & Code Quality Review**  
- **Phase 8: Final Validation, Submission Packaging & Demo Preparation**

---

## 1. Project Overview & Problem Statement

### 1.1 Problem Statement
Modern wealth management and asset allocation teams face fragmented financial data across disconnected spreadsheets and ledgers. Portfolio managers, analysts, and executive stakeholders require instantaneous, highly accurate answers to complex investment queries:
- Querying structured financial records (holdings, transactions, benchmark comparisons) without manual SQL authoring.
- Calculating precise sector exposure breakdowns that strictly segregate equities from fixed-income bond holdings.
- Interacting conversationally while retaining context across multi-turn dialogues.
- Guaranteeing enterprise-grade read-only database security with zero risk of SQL injection or data corruption.
- Verifying agent reliability against ground-truth benchmarks with auditable precision.

### 1.2 Solution Overview
The PL Capital AI Portfolio Analytics Agent delivers an end-to-end, enterprise-grade AI system featuring:
1. **Relational Database Foundation (Phase 1):** Ingests all 9 assessment CSV datasets into SQLite with strict foreign key constraints (`PRAGMA foreign_keys = ON;`), correct data types, intelligent NULL handling (bonds vs equities), and data integrity verification.
2. **Secure Text-to-SQL Engine (Phase 2):** Converts natural language into read-only, validated SQLite queries with kernel-level authorizer callbacks, CTE support, and protection against injection or unauthorized table access.
3. **Sector Exposure Calculator (Phase 3):** Combines holding weights with security sector mappings, strictly excludes bond holdings, and normalizes equity percentage exposures.
4. **Agent Tool Orchestrator (Phase 4):** A unified AI Agent powered by Google Gemini native function calling, deterministic semantic fallback routing, bounded multi-turn conversation memory, and Ground Truth evaluation benchmarking.
5. **Evaluation Benchmark & Reporting (Phase 5):** End-to-end evaluation engine testing all 10 ground truth questions against the actual `PortfolioAgent`, computing category-specific metrics, semantic SQL comparisons (ordered/unordered with float tolerance), bond exclusion verification, reproducible artifact export (`.json`, `.csv`, `.md`), and deep root-cause analysis of dataset edge cases.
6. **Professional Streamlit Dashboard (Phase 6):** Full-featured dark navy & charcoal investment analytics dashboard with 5 distinct pages: Executive Overview, AI Portfolio Assistant (chat with tool inspection), Sector Exposure Analytics (Plotly donut & bar charts), Portfolio Explorer, and Benchmark Evaluator.
7. **Final Submission Audit & Packaging (Phases 7 & 8):** Complete code quality review, fresh virtual environment verification, reproducible packaging, and documentation guides.

---

## 2. Technology Stack

- **Language:** Python 3.10+
- **Frontend Dashboard:** Streamlit 1.64+, Plotly 5.15+
- **LLM SDK:** `google-genai>=0.10.0` (version 3.0.0 installed)
- **Model:** Configurable via `GEMINI_MODEL` (default: `gemini-3.8-flash`)
- **Database:** SQLite 3 (with foreign key enforcement, WAL mode, and Authorizer callbacks)
- **Data Engineering:** Pandas, NumPy
- **Environment Management:** python-dotenv
- **Testing Framework:** Pytest (108 automated tests covering all phases, edge cases, UI data pipelines, and evaluation metrics: 106 passed, 2 skipped)

---

## 3. Database Schema & Relational Design

The database comprises 9 relational tables populated from assessment CSV datasets with strict primary keys, foreign keys, and asset-type integrity checks:

| Table Name | Primary Key | Description & Key Columns | Row Count |
| :--- | :--- | :--- | :---: |
| `sectors` | `sector_id` | Industry sector reference (e.g., Technology, Healthcare, Financials) | 10 |
| `benchmarks` | `benchmark_id` | Benchmark indices (S&P 500, Russell 2000, Bloomberg US Aggregate) | 13 |
| `portfolios` | `portfolio_id` | Portfolios with `portfolio_name`, `strategy_type`, `target_risk_level`, `current_aum`, `is_active` | 13 |
| `securities` | `security_id` | Financial assets: `ticker`, `security_name`, `asset_type` (Stock/Bond), `sector_id`, `current_price` | 30 |
| `holdings` | `holding_id` | Portfolio asset allocations: `portfolio_id`, `security_id`, `quantity`, `cost_basis`, `current_weight` | 95 |
| `transactions` | `transaction_id`| Ledger executions: `portfolio_id`, `security_id`, `transaction_type` (BUY/SELL), `trade_date`, `amount` | 24 |
| `historical_prices`| `price_id` | Daily pricing series: `security_id`, `price_date`, `close_price`, `volume` | 330 |
| `portfolio_performance`| `perf_id`| Time-series returns: `portfolio_id`, `date`, `daily_return`, `cumulative_return`, `nav` | 44 |
| `risk_metrics`| `metric_id` | Quantitative risk stats: `portfolio_id`, `calculation_date`, `sharpe_ratio`, `volatility`, `var_95` | 44 |

- **Integrity Rule for Assets:** Stocks require a valid `sector_id`; Bonds require `coupon_rate`, `maturity_date`, and `face_value`, with `sector_id = NULL`.
- **Enforcement:** `PRAGMA foreign_keys = ON;` is enforced on every connection; violations are strictly forbidden.

---

## 4. Directory Structure

```text
portfolio-analytics-agent/
│
├── agent/                         # AI Agent and tool orchestration layer
│   ├── __init__.py                # Package exports
│   ├── conversation_manager.py    # Multi-turn memory, context bounding, and follow-up enrichment
│   ├── llm_client.py              # Modern google-genai client, retry, backoff, and connectivity
│   ├── portfolio_agent.py         # Primary AI Agent orchestrator & response synthesizer
│   ├── sql_generator.py           # SchemaContextBuilder and prompt-to-SQL engine
│   ├── sql_validator.py           # AST/token parser and SQLite kernel-level authorizer
│   └── tool_registry.py           # Gemini function calling tool declarations and validation
│
├── tools/                         # Analytical and execution tools
│   ├── __init__.py                # Package exports
│   ├── exposure_calculator.py     # ExposureCalculator: equity sector breakdown (bonds excluded)
│   └── sql_tool.py                # SQLQueryTool: execution, timing, and structured envelopes
│
├── database/                      # Core database access, ingestion, and validation
│   ├── __init__.py                # Public interface exports
│   ├── config.py                  # Settings (.env), allowed tables, and query limits
│   ├── connection.py              # DatabaseManager with context management & strict FK enforcement
│   ├── database_schema.sql        # Exact SQL DDL definitions, constraints, and indices
│   ├── exceptions.py              # Typed exception hierarchy
│   ├── ingestion.py               # CSVIngestionService: idempotent CSV ingestion
│   ├── logger.py                  # Structured console and file logging
│   ├── schema.py                  # Schema loader, table creation & migration
│   └── validator.py               # Table existence, count, FK, PK, and NULL validation
│
├── evaluation/                    # Agent evaluation benchmark engine
│   ├── __init__.py
│   ├── evaluator.py               # Automated benchmark runner across all 10 ground truth questions
│   ├── ground_truth_dataset.json  # Assessment ground truth questions & SQL queries
│   └── results/                   # Reproducible benchmark artifact exports
│       ├── benchmark_results.json # Full JSON structured results with metadata
│       ├── benchmark_results.csv  # Excel-ready tabular results
│       └── benchmark_summary.md   # Executive summary markdown scorecard
│
├── data/                          # 9 Preserved assessment CSV datasets
│   ├── benchmarks.csv
│   ├── historical_prices.csv
│   ├── holdings.csv
│   ├── portfolio_performance.csv
│   ├── portfolios.csv
│   ├── risk_metrics.csv
│   ├── sectors.csv
│   ├── securities.csv
│   └── transactions.csv
│
├── .streamlit/                    # Streamlit server and theme configuration
│   └── config.toml                # Native dark navy theme settings
│
├── docs/                          # Submission documentation & demo guides
│   ├── FINAL_SUBMISSION_GUIDE.md  # Detailed setup, CLI, dashboard & evaluation guide
│   ├── FINAL_DEMO_CHECKLIST.md    # Step-by-step evaluator walkthrough script
│   └── FINAL_VALIDATION_REPORT.md # Verification metrics, test logs & compliance report
│
├── tests/                         # Automated test suite (108 unit & integration tests)
│   ├── __init__.py
│   ├── conftest.py                # Pytest fixtures (in-memory & file DBs, seeders, Gemini mock isolation)
│   ├── test_connection.py         # Connection manager & FK enforcement tests
│   ├── test_conversation_manager.py# Multi-turn memory, context resolution & bounding tests
│   ├── test_dashboard.py          # Phase 6 Streamlit UI data pipelines & integration tests
│   ├── test_evaluator.py          # Phase 5 benchmark, semantic comparison & Q7/Q8 tests
│   ├── test_exposure_calculator.py# Exposure calculator, bond exclusion & 11 edge case tests
│   ├── test_ingestion.py          # Data types, NULLs & duplicate prevention tests
│   ├── test_integration.py        # End-to-end Phase 1 pipeline tests
│   ├── test_model_configuration.py# Model configuration, shared client & live/mock honesty tests
│   ├── test_portfolio_agent.py    # Agent orchestration, tool selection & 12 required test conditions
│   ├── test_schema.py             # Table and index creation tests
│   ├── test_sql_generator.py      # Schema context, prompt assembly, and cleaning tests
│   ├── test_sql_tool.py           # SQLQueryTool tests and Ground Truth evaluation (Q1-Q8)
│   ├── test_sql_validator.py      # Security checks, bans, and authorizer callback tests
│   ├── test_tool_registry.py      # Tool registration, arguments, and dispatching tests
│   └── test_validation.py         # Database validation utilities tests
│
├── logs/                          # Application runtime logs
│   ├── .gitkeep
│   └── database.log
│
├── .env.example                   # Environment variable template
├── .gitignore                     # Git ignore rules for DBs, logs, caches
├── app.py                         # Diagnostic CLI & Streamlit-ready app
├── streamlit_app.py               # Phase 6 Dedicated Streamlit Dashboard
├── main.py                        # Primary CLI pipeline & agent entry point
├── README.md                      # Comprehensive documentation
└── requirements.txt               # Project dependencies
```

---

## 5. Streamlit Dashboard Architecture

The dashboard is accessible via `streamlit_app.py` and implements a dark navy and charcoal theme (`#0B1120`, `#1E293B`, `#38BDF8`, `#94A3B8`) designed for investment analytics:

### Page 1 — Executive Overview
- **Metric Cards:** Total Portfolios (13), Active Portfolios (10), Total Securities (30), Total AUM ($276.5M).
- **Interactive Visualizations:**
  - Securities Distribution by Industry Sector (horizontal bar chart).
  - Portfolio Distribution by Target Risk Level (High, Medium, Low donut chart).
  - Total Assets Under Management (AUM) by Portfolio comparison chart.
- **Recent Transactions:** Real ledger records from `transactions` table with timestamps, quantities, and executed amounts.

### Page 2 — AI Portfolio Assistant
- **Conversational Chat Interface:** Interactive multi-turn chat powered by `PortfolioAgent`.
- **Memory & Context:** Multi-turn session memory bounding context and pronoun resolution.
- **Tool Inspection:** Expandable dropdowns displaying the selected tool (`sql_query_tool` vs `exposure_calculator`), generated SQL queries, tabular query results, and execution latency.
- **Suggested Prompts:** One-click quick question chips.
- **Reset Button:** Instantly clears session state and conversation memory.
- **Mode Indicators:** Clear badges distinguishing live Gemini execution (`[LIVE GEMINI API]`) from deterministic offline execution (`[OFFLINE / MOCK ACTIVE]`).

### Page 3 — Sector Exposure Analytics
- **Interactive Portfolio Selector:** Dropdown to select any of the 13 portfolios.
- **Precision Calculation:** Invokes `ExposureCalculator` to normalize equity sector weights while **strictly excluding bond holdings**.
- **Interactive Visualizations:**
  - Plotly Donut Chart of sector allocations.
  - Plotly Horizontal Bar Chart of exposure percentages.
- **Holdings Table:** Complete breakdown of underlying securities, highlighting asset type (`Stock` vs `Bond`).
- **Edge Case Handling:** Gracefully handles bond-only portfolios (e.g. `Total Bond Market Index Fund` showing 0 equities and 6 excluded bonds).

### Page 4 — Portfolio Explorer
- **Granular Portfolio Metadata:** Strategy type, target risk level, benchmark index, inception date, and AUM.
- **Holdings & Market Values:** Interactive, sortable table calculating current market values (`quantity * current_price`) and portfolio weights.
- **Asset Allocation Charts:** Equity vs Fixed Income breakdown and Sector distribution.
- **Performance & Risk Tabs:** Historical NAV, returns (1M, 3M, 6M, 1Y), Sharpe ratio, and Value at Risk (VaR 95) metrics.

### Page 5 — Agent Evaluation & Benchmark Reporting
- **Evaluation Controls:** Explicit "Run Full Benchmark" button (does not auto-run on page refresh).
- **Dual Mode Support:** Switch between `Mock / Offline` and `Live Gemini API`.
- **Metrics Display:** Tool Routing Accuracy (100%), SQL Generation (100%), SQL Execution (100%), Data Accuracy (100%), and Latencies.
- **Interactive Scorecard:** 10-question evaluation table with individual pass/fail badges.
- **Deep Dive Expander:** Detailed documentation of the Q7 (8 portfolios) and Q8 (1 portfolio) database investigation.
- **Downloadable Reports:** Direct download buttons for `benchmark_results.json`, `benchmark_results.csv`, and `benchmark_summary.md`.

---

## 6. How to Launch the Streamlit Dashboard

Run the application using Streamlit:

```bash
streamlit run streamlit_app.py
```
*(Or via Python module: `python -m streamlit run streamlit_app.py`)*

The application will open in your browser at `http://localhost:8501`.

---

## 7. Command-Line CLI Operations

All existing command-line capabilities are preserved:

### 7.1 Interactive CLI Agent
```bash
python main.py --agent
```

### 7.2 Direct Query CLI
```bash
python main.py --ask "What are the sector exposures for Tech Innovation Fund?"
python main.py --ask "How many portfolios do we have in total?"
```

### 7.3 Database Pipeline Operations
```bash
# Full reset, ingestion, and validation:
python main.py --reset

# Schema initialization only:
python main.py --init

# CSV dataset ingestion only:
python main.py --ingest

# Integrity constraint validation only:
python main.py --validate

# Fast diagnostic status:
python app.py
```

### 7.4 Run Ground Truth Benchmark
```bash
# Offline deterministic mode:
python main.py --evaluate --mode mock

# Live Gemini API mode (requires GEMINI_API_KEY in .env):
python main.py --evaluate --mode live
```

### 7.5 Run Complete Test Suite (108 Tests)
```bash
python -m pytest tests/ -v
```

---

## 8. Evaluation Benchmark Results (Mock Mode)

| ID | Diff | Type | Expected Tool | Routing | Exec | Accuracy | Latency | Status |
| :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| Q1 | Easy | text2sql | `sql_query_tool` | OK | OK | PASS | 2.10 ms | **PASS** |
| Q2 | Easy | text2sql | `sql_query_tool` | OK | OK | PASS | 2.52 ms | **PASS** |
| Q3 | Easy | text2sql | `sql_query_tool` | OK | OK | PASS | 3.58 ms | **PASS** |
| Q4 | Medium | text2sql | `sql_query_tool` | OK | OK | PASS | 2.00 ms | **PASS** |
| Q5 | Medium | text2sql | `sql_query_tool` | OK | OK | PASS | 2.93 ms | **PASS** |
| Q6 | Medium | text2sql | `sql_query_tool` | OK | OK | PASS | 2.49 ms | **PASS** |
| Q7 | Hard | text2sql | `sql_query_tool` | OK | OK | PASS | 2.69 ms | **PASS** |
| Q8 | Hard | text2sql | `sql_query_tool` | OK | OK | PASS | 2.69 ms | **PASS** |
| Q9 | Medium | exposure_calculator | `exposure_calculator` | OK | OK | PASS | 4.70 ms | **PASS** |
| Q10 | Medium | exposure_calculator | `exposure_calculator` | OK | OK | PASS | 6.79 ms | **PASS** |

- **Total Questions:** 10 / 10
- **Tool Routing Accuracy:** 100.0% (10/10)
- **Data / Answer Accuracy:** 100.0% (10/10)
- **Average Latency:** 5.07 ms

---

## 9. Mandatory Investigation: Q7 & Q8 Database Discrepancy

- **Question 7 (Tech sector holdings percentage across portfolios):**
  - **Ground Truth Query:** Joins `portfolio_tech_value` with `portfolio_total_value` via an `INNER JOIN`.
  - **Database Truth:** Exactly **8 portfolios** hold Technology stocks. The other 5 portfolios hold 0% Technology.
  - **Verdict:** Strictly produces **8 rows**. The Phase 4 markdown table erroneously stated "10 portfolios" by conflating the total active portfolio count (10) with tech-holding portfolios (8).
- **Question 8 (Portfolios with >5 sectors):**
  - **Ground Truth Query:** Filters `WHERE s.asset_type = 'Stock' GROUP BY ... HAVING COUNT(DISTINCT sec.sector_id) > 5`.
  - **Database Truth:** Exactly **1 portfolio** (`Total Stock Market Index Fund`) holds 6 distinct equity sectors. All other portfolios hold $\le 4$ sectors.
  - **Verdict:** Strictly produces **1 row**. The prior Phase 4 text mentioning "2 diversified portfolios" was a clerical typo in the summary narrative.

---

## 10. Known Limitations & Production Readiness

1. **Gemini Live Quota & Error Transparency:** Live mode requires an active `GEMINI_API_KEY` with available quota. When rate limits (`429 RESOURCE_EXHAUSTED`) or network connectivity issues occur, LIVE mode honestly surfaces the error and records it without silent mock masking. For automated CI/CD and offline testing, the offline mock mode (`--mode mock`) provides complete, deterministic benchmark execution without requiring live API quota.
2. **Natural Language Join Ambiguity:** Questions asking for "all portfolios" with specific sector filters (e.g., Tech holdings) omit zero-exposure portfolios unless the query explicitly specifies `LEFT JOIN` and `COALESCE`.
3. **Strict Read-Only Enforcement:** Queries attempting DDL, DML, PRAGMA, or SQLite internal table access are rejected at both AST and SQLite engine authorizer levels.

---

## 11. Additional Submission Documents

Detailed documentation is available in the [`docs/`](docs/) directory:
- [`docs/FINAL_SUBMISSION_GUIDE.md`](docs/FINAL_SUBMISSION_GUIDE.md) — Complete setup, configuration, CLI & Streamlit guide.
- [`docs/FINAL_DEMO_CHECKLIST.md`](docs/FINAL_DEMO_CHECKLIST.md) — Step-by-step presentation & evaluator walkthrough.
- [`docs/FINAL_VALIDATION_REPORT.md`](docs/FINAL_VALIDATION_REPORT.md) — Verification results, test metrics & compliance audit.
