# Copilot Instructions

This workspace contains a multi-agent contract lifecycle management system built on Microsoft Copilot Studio, plus a Python microservice for document automation.

## Projects

### Copilot Studio Agents (`.mcs.yml` files)

Six agents in a **hub-and-spoke architecture**:

- **ContractAgent/** — Orchestrator. Routes work to five sub-agents and consolidates results. Contains child agent references in `ContractAgent/agents/` and knowledge sources (SharePoint) in `ContractAgent/knowledge/`.
- **ContractIntakeAgent/** — Classifies contracts (Vendor, Customer, NDA, Partnership, Maintenance) and assesses urgency (Standard 30-day, Expedited 14-day, Critical 7-day).
- **LegalReviewAgent/** — Reviews clauses against Contoso's legal playbook. Flags deviations as Major/Moderate/Minor risk with approved alternative language.
- **ComplianceRiskAgent/** — Checks tax, insurance, cybersecurity (SOC 2, ISO 27001), and regulatory compliance. Scores Green/Yellow/Red.
- **ReportingAgent/** — Extracts key terms, compiles findings, generates executive summaries with Must Fix/Should Fix/Consider recommendations.
- **PortfolioIntelligenceAgent/** — Queries Microsoft Fabric lakehouse for benchmarks, spend analytics, vendor performance, and renewal risks.

Each agent directory contains `agent.mcs.yml` (instructions and metadata), `settings.mcs.yml` (configuration), and `topics/*.mcs.yml` (conversation flows). The orchestrator's `settings.mcs.yml` has `GenerativeActionsEnabled: true` and uses a `GenerativeAIRecognizer`.

**Routing pipeline:** User → Orchestrator → Intake → Legal → Compliance → Reporting. Portfolio Intelligence is invoked on-demand for benchmarking queries.

### Contract Redline Tool (`ContractRedlineTool/`)

Python FastAPI microservice that applies tracked changes to Word documents via OpenXML manipulation and uploads results to SharePoint via Microsoft Graph API.

**Build & Run:**
```bash
cd ContractRedlineTool
pip install -r requirements.txt
cp .env.example .env          # configure Azure credentials
uvicorn app.main:app --reload --port 8000
```

**Run tests:**
```bash
cd ContractRedlineTool
pytest                              # full suite
pytest tests/test_redline_engine.py # single file
pytest -k "test_apply_single_change" # single test
```

**Docker:**
```bash
docker build -t contract-redline-tool .
docker run -p 8000:8000 --env-file .env contract-redline-tool
```

**Deploy (Bicep):**
```bash
az deployment group create \
  --resource-group rg-contract-agent \
  --template-file deploy/bicep/main.bicep \
  --parameters namePrefix=contract-redline
```

### Documentation (`documentation/`)

- `solution.md` / `design.md` — Architecture and design decisions
- `requirements.md` — Business requirements and success metrics
- `redline-tool.md` — Redline Tool technical specification
- `sample-data/` — Sample contracts, policy docs, compliance checklists, test scenarios, and Fabric lakehouse CSVs

### Personas (`persona/`)

Four stakeholder personas (Procurement, Legal, Compliance, Finance) used for scenario testing and agent instruction design.

## Architecture

### Agent Communication

Sub-agents are registered as **connected agents** in the orchestrator (`ContractAgent/agents/*/agent.mcs.yml`). Each uses `AgentDialog` kind with `OnToolSelected` triggers. The orchestrator invokes them via Copilot Studio's connected agent framework — no direct agent-to-agent calls.

Sub-agents declare typed inputs/outputs (e.g., `ContractDetails`, `ComplianceArea` → `ComplianceScore`, `TaxStatus`). Topic flows use `SearchAndSummarizeContent` for RAG-style knowledge queries and `ConditionGroup` for deterministic branching.

### Redline Tool Architecture

```
POST /api/redline → Download .docx from SharePoint (Graph API)
                  → Apply tracked changes (lxml/python-docx OpenXML)
                  → Add Word comments with risk-rated rationale
                  → Upload redlined .docx back to SharePoint
                  → Return results with SharePoint URL
```

Key modules:
- `app/main.py` — FastAPI app with CORS and API key auth (`X-API-Key` header)
- `app/config.py` — `pydantic-settings` configuration (reads `.env`)
- `app/services/redline_engine.py` — OpenXML manipulation: `<w:del>`/`<w:ins>` tracked changes, `<w:comment>` with risk emoji markers (🔴 Major, 🟡 Moderate, 🟢 Minor)
- `app/services/graph_client.py` — Microsoft Graph client with `ClientSecretCredential` (dev) or `DefaultAzureCredential` (production Managed Identity)
- `app/models/schemas.py` — Pydantic request/response models with `RiskLevel` enum
- `app/routers/redline.py` — Single `POST /api/redline` endpoint

## Conventions

- **Copilot Studio YAML**: All agent files use `.mcs.yml` extension. The orchestrator's schema name (`cr57c_agentqf4ruA`) appears in knowledge source filenames and settings.
- **Risk classification**: Three-tier system used consistently across all agents — Major (🔴), Moderate (🟡), Minor (🟢). Maps to `RiskLevel` enum in the Redline Tool.
- **Policy grounding**: Agents must cite specific policy sections. If guidance isn't in knowledge sources, agents say so rather than using general model knowledge.
- **Model hint**: All agents specify `modelNameHint: opus4-1` in their `aISettings`.
- **Redline Tool auth**: API key via `X-API-Key` header. Key is optional in dev (empty string skips validation).
- **Graph API auth**: Client secret locally, system-assigned Managed Identity in production. Required permissions: `Sites.ReadWrite.All`, `Files.ReadWrite.All`.
- **Test patterns**: Pytest with `TestClient` (FastAPI), `tmp_path` for temp Word docs, `unittest.mock.patch` for Graph API calls. Tests create real `.docx` files and verify OpenXML output.
- **Deployment target**: Azure App Service (Linux, Python 3.11) in `canadacentral` region, resource group `rg-contract-agent`.

## Deploying the Fabric Lakehouse & Data Agent

The Portfolio Intelligence Agent queries a Microsoft Fabric lakehouse for portfolio-level analytics. The sample data lives in `documentation/sample-data/fabric/` as five CSV files that must be loaded into lakehouse Delta tables, then exposed via a Fabric Data Agent connected to Copilot Studio.

### Prerequisites

- A paid **F2 or higher** Fabric capacity (or Power BI Premium P1+) with Microsoft Fabric enabled
- **Fabric data agent tenant settings** enabled in the Fabric admin portal:
  - Fabric data agent → Enabled
  - Cross-geo processing for AI → Enabled
  - Cross-geo storing for AI → Enabled
- **Standalone Copilot experience** enabled in the Power BI admin portal (Tenant settings → Copilot → Standalone Copilot experience)
- A Fabric workspace where you can create lakehouse and data agent items

### Step 1: Create the Lakehouse

1. In [Microsoft Fabric](https://fabric.microsoft.com), navigate to your workspace
2. Select **+ New item** → search for **Lakehouse** → select **Lakehouse**
3. Name it `ContractPortfolioLH` (or similar) → **Create**

### Step 2: Upload CSV Files and Load as Delta Tables

The five CSV files in `documentation/sample-data/fabric/` must be loaded as lakehouse tables. The data agent cannot query raw files — only Delta tables.

**Option A — Manual upload via portal:**

1. In the lakehouse, select the **Files** section → **Upload** → **Upload files**
2. Upload all five CSVs: `contracts.csv`, `contract_clauses.csv`, `vendors.csv`, `compliance_incidents.csv`, `spend_actuals.csv`
3. For each uploaded CSV: right-click → **Load to tables** → **New table** → ensure "Column header" is checked → **Load**
4. Verify five tables appear under **Tables** in the lakehouse explorer

**Option B — Notebook (programmatic):**

1. Create a new notebook in the same workspace, attach the lakehouse as a data source
2. Run the following to load all CSVs as Delta tables:

```python
import os

csv_files = [
    "contracts",
    "contract_clauses",
    "vendors",
    "compliance_incidents",
    "spend_actuals",
]

# Upload the CSV files to the lakehouse Files section first,
# then run this to convert them to Delta tables:
for table_name in csv_files:
    df = (
        spark.read.option("header", "true")
        .option("inferSchema", "true")
        .csv(f"Files/{table_name}.csv")
    )
    df.write.mode("overwrite").saveAsTable(table_name)
    print(f"Loaded {table_name}: {df.count()} rows")
```

3. After running, stop the notebook session to release capacity

### Lakehouse Schema Reference

| Table | Rows | Key Columns | Relationships |
|-------|------|-------------|---------------|
| `contracts` | 50 | `contract_id` (PK), `vendor_id` (FK→vendors), `contract_type`, `total_value`, `status`, `expiration_date` | Master contract records |
| `contract_clauses` | 227 | `clause_id` (PK), `contract_id` (FK→contracts), `clause_type`, `risk_score`, `deviation_type`, `standard_compliant` | Clause-level detail per contract |
| `vendors` | 20 | `vendor_id` (PK), `vendor_name`, `vendor_type` (tier), `compliance_score`, `country` | Vendor master data |
| `compliance_incidents` | 30 | `incident_id` (PK), `contract_id` (FK→contracts), `vendor_id` (FK→vendors), `severity`, `incident_type` | Historical compliance issues |
| `spend_actuals` | 181 | `record_id` (PK), `contract_id` (FK→contracts), `vendor_id` (FK→vendors), `fiscal_year`, `budgeted_amount`, `actual_amount`, `variance_pct` | Budget vs. actual spend by period |

### Step 3: Create the Fabric Data Agent

1. In your Fabric workspace, select **+ New item** → search for **Data agent** → select **Fabric data agent**
2. Name it `Contract Portfolio Intelligence` → **Create**
3. **Select data source:** Choose the `ContractPortfolioLH` lakehouse → **Add**
4. **Select tables:** Check all five tables: `contracts`, `contract_clauses`, `vendors`, `compliance_incidents`, `spend_actuals`

### Step 4: Add Data Agent Instructions

Select **Data agent instructions** and add:

```
This data source contains Contoso's enterprise contract portfolio data across five tables:

- contracts: Master contract records with 50 contracts across types (SOW, NDA, MSA, SLA, Vendor Agreement). Key fields: contract_id, vendor_id, contract_type, total_value, annual_value, status, effective_date, expiration_date, payment_terms_days, auto_renewal, risk_rating, department.

- contract_clauses: 227 clause-level records linked to contracts. Key fields: contract_id, clause_type, standard_compliant (boolean), deviation_type (Major/Moderate/Minor/None), risk_score (1-10), review_status, recommendation.

- vendors: 20 vendor records with tier classification. Key fields: vendor_id, vendor_name, vendor_type (Strategic/Preferred/Standard/Probationary), compliance_score (0-100), country, total_contract_value, active_contracts_count.

- compliance_incidents: 30 historical compliance incidents. Key fields: contract_id, vendor_id, incident_type, severity (High/Medium/Low), detected_date, resolved_date, financial_impact.

- spend_actuals: 181 quarterly spend records. Key fields: contract_id, vendor_id, fiscal_year, fiscal_quarter, budgeted_amount, actual_amount, variance_pct, spend_category, department.

Use contracts.vendor_id to join with vendors.vendor_id. Use contracts.contract_id to join with contract_clauses, compliance_incidents, and spend_actuals.

When answering benchmarking questions, provide averages, medians, and percentile context. When analyzing spend, compute variance as (actual - budgeted) / budgeted * 100. Vendor risk ratings map to tiers: Strategic > Preferred > Standard > Probationary.
```

### Step 5: Add Example Queries

Select **Example queries** and add these question-SQL pairs for the lakehouse:

**Question:** What contracts are expiring in the next 90 days?
```sql
SELECT c.contract_id, c.title, c.vendor_name, c.expiration_date, c.total_value, c.auto_renewal,
       v.compliance_score, v.vendor_type
FROM contracts c
LEFT JOIN vendors v ON c.vendor_id = v.vendor_id
WHERE c.expiration_date BETWEEN CURRENT_DATE AND DATEADD(DAY, 90, CURRENT_DATE)
  AND c.status = 'Active'
ORDER BY c.expiration_date ASC
```

**Question:** Show spend variance by vendor for the current fiscal year
```sql
SELECT v.vendor_name, v.vendor_type,
       SUM(s.budgeted_amount) AS total_budget,
       SUM(s.actual_amount) AS total_actual,
       SUM(s.variance_amount) AS total_variance,
       ROUND(AVG(s.variance_pct), 1) AS avg_variance_pct
FROM spend_actuals s
JOIN vendors v ON s.vendor_id = v.vendor_id
WHERE s.fiscal_year = 'FY2025'
GROUP BY v.vendor_name, v.vendor_type
ORDER BY total_variance DESC
```

**Question:** Which vendors have the most compliance incidents?
```sql
SELECT v.vendor_name, v.vendor_type, v.compliance_score,
       COUNT(ci.incident_id) AS incident_count,
       SUM(CASE WHEN ci.severity = 'High' THEN 1 ELSE 0 END) AS high_severity,
       SUM(ci.financial_impact) AS total_financial_impact
FROM vendors v
LEFT JOIN compliance_incidents ci ON v.vendor_id = ci.vendor_id
GROUP BY v.vendor_name, v.vendor_type, v.compliance_score
HAVING COUNT(ci.incident_id) > 0
ORDER BY incident_count DESC
```

**Question:** What is the average payment term by contract type and vendor tier?
```sql
SELECT c.contract_type, v.vendor_type,
       ROUND(AVG(c.payment_terms_days), 0) AS avg_payment_days,
       COUNT(*) AS contract_count,
       ROUND(AVG(c.total_value), 2) AS avg_contract_value
FROM contracts c
JOIN vendors v ON c.vendor_id = v.vendor_id
GROUP BY c.contract_type, v.vendor_type
ORDER BY c.contract_type, v.vendor_type
```

### Step 6: Test and Publish the Data Agent

1. Use the built-in chat pane in the data agent editor to test questions
2. Verify responses return accurate data from all five tables
3. Once satisfied, select **Publish** → **Publish** to generate the published URL
4. Note the published URL — you'll need it for the Copilot Studio connection

### Step 7: Connect to the Portfolio Intelligence Agent in Copilot Studio

1. Open [Copilot Studio](https://copilotstudio.microsoft.com) and navigate to the **Contract Management Orchestrator** agent (or the Portfolio Intelligence Agent directly)
2. Go to **Agents** (top pane) → **+ Add**
3. Select **Microsoft Fabric** from the connector categories
4. Create a new connection (or select existing) to Microsoft Fabric
5. Select the `Contract Portfolio Intelligence` data agent from the list → **Next**
6. Adjust the description to match the Portfolio Intelligence Agent's role → **Add agent**
7. Under the connected agent's additional details, set authentication to **User authentication** (ensures per-user data access permissions) or **Agent author authentication** (uses the author's permissions for all users)
8. Ensure **Generative AI orchestration** is enabled: **Settings** (top of test pane) → **Orchestration** → select the first option
9. **Publish** the agent to activate the connection

### Verification

Test the full pipeline by asking the orchestrator questions like:
- "How does this contract compare to our historical portfolio?"
- "Show me spend variance for Q1 FY2025"
- "Which vendors have compliance issues?"
- "What contracts are expiring in the next 60 days?"

The orchestrator should route these to the Portfolio Intelligence Agent, which invokes the Fabric Data Agent to query the lakehouse and return data-grounded responses.
