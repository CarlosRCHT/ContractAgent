# Contract Agent

A multi-agent contract lifecycle management system built on Microsoft Copilot Studio, with a Python microservice for automated document redlining. The solution reduces contract review cycles from months to hours by orchestrating specialized AI agents for intake classification, legal review, compliance risk assessment, portfolio benchmarking, and executive reporting.

## Architecture

```mermaid
graph TD
    User["User / Teams"]

    subgraph Orchestrator["Contract Management Orchestrator (ContractAgent — Hub)"]
        direction TB
        KS["Knowledge Sources (SharePoint):<br/>Corporate Procurement Policy · Legal Review Playbook<br/>Compliance Checklist · Contract Templates"]
        Intake["Intake Agent"]
        Legal["Legal Review Agent"]
        Compliance["Compliance Risk Agent"]
        Reporting["Reporting Agent"]
        Portfolio["Portfolio Intelligence Agent"]
    end

    User --> Orchestrator
    Portfolio --> Fabric["Fabric Data Agent /<br/>Lakehouse"]
    Orchestrator --> Redline["Contract Redline Tool<br/>(FastAPI)<br/>Azure App Service"]
    Redline --> SharePoint["SharePoint<br/>(Source & Output)"]
```

### Review Pipeline

```mermaid
graph LR
    Submit["User submits contract"] --> Intake["Intake Agent:<br/>classify type & urgency"]
    Intake --> Legal["Legal Review Agent:<br/>clause-by-clause<br/>playbook review"]
    Legal --> Compliance["Compliance Risk Agent:<br/>tax, insurance, cyber,<br/>regulatory checks"]
    Compliance --> Portfolio["Portfolio Intelligence Agent:<br/>benchmark against<br/>historical portfolio"]
    Portfolio --> Reporting["Reporting Agent:<br/>executive summary with<br/>recommendations"]
    Reporting --> Redline["Contract Redline Tool:<br/>apply tracked changes<br/>to Word document"]
```

## Repository Structure

```
ContractAgent/
├── ContractAgent/             # Orchestrator agent (hub)
│   ├── agent.mcs.yml          # Agent instructions & config
│   ├── settings.mcs.yml       # Copilot Studio settings
│   ├── agents/                # Connected sub-agent references
│   │   ├── ComplianceRiskAgent/
│   │   ├── ContractIntakeAgent/
│   │   ├── LegalReviewAgent/
│   │   ├── PortfolioIntelligenceAgent/
│   │   └── ReportingAgent/
│   ├── knowledge/             # SharePoint knowledge source configs
│   └── topics/                # Conversation flow topics
├── ContractIntakeAgent/       # Contract classification & triage
├── LegalReviewAgent/          # Clause review against legal playbook
├── ComplianceRiskAgent/       # Multi-domain compliance checks
├── ReportingAgent/            # Executive summary generation
├── PortfolioIntelligenceAgent/# Lakehouse analytics & benchmarking
├── ContractRedlineTool/       # Python FastAPI microservice
│   ├── app/                   # Application code
│   ├── tests/                 # Pytest test suite
│   └── deploy/                # Bicep IaC & deployment config
├── documentation/             # Architecture, design, requirements
│   └── sample-data/           # Sample contracts, policies, Fabric CSVs
└── persona/                   # Stakeholder personas for testing
```

## Copilot Studio Agents

All agents use `.mcs.yml` format and specify `modelNameHint: opus4-1`. The orchestrator uses `GenerativeAIRecognizer` with `GenerativeActionsEnabled: true` for dynamic routing.

### Contract Intake Agent

Classifies contracts and assesses review urgency.

| Capability | Details |
|---|---|
| **Contract Types** | Vendor Services, Customer Agreement, NDA, Partnership, Maintenance |
| **Urgency Levels** | Standard (30-day), Expedited (14-day), Critical (7-day) |
| **Routing Rules** | Vendor > $100K → Legal + Tax + Insurance; IT/data contracts → add Cybersecurity |
| **Metadata Collected** | Parties, value, term, jurisdiction, special considerations |

**Topics:** `ContractClassification`, `UrgencyAssessment`, `ConversationStart`

### Legal Review Agent

Reviews contracts clause-by-clause against Contoso's legal playbook.

| Capability | Details |
|---|---|
| **Review Priority** | Liability → Indemnification → Termination → IP → Confidentiality → Data Protection → Force Majeure → Governing Law → Insurance → Payment |
| **Risk Levels** | Major 🔴 (VP Legal, 15-day SLA), Moderate 🟡 (Senior Counsel, 10-day), Minor 🟢 (notation, 5-day) |
| **Prohibited Terms** | Unlimited liability, auto-renewal > 3 years, exclusive dealing without board approval, non-compete > 2 years, jury trial waivers, unilateral price increases, liquidated damages > 15% |

**Topics:** `RiskAssessment`, `PlaybookReview`, `ConversationStart`

### Compliance Risk Agent

Verifies compliance across four domains with Green/Yellow/Red scoring.

| Domain | Key Checks |
|---|---|
| **Tax** | Domestic sales tax, regional tax, withholding tax (25% default / treaty-reduced), transfer pricing, BEPS |
| **Insurance** | Tiered minimums ($2M / $5M / $10M by contract value), Contoso as additional insured, AM Best A- rating, 30-day cancellation notice |
| **Cybersecurity** | SOC 2 Type II, ISO 27001, PCI DSS, data residency, 72-hour breach notification, AES-256 at rest, TLS 1.2+ in transit, MFA, annual pen testing |
| **Regulatory** | Data privacy regulations, industry-specific, multilingual requirements, WCAG 2.1 AA accessibility |

**Topics:** `InsuranceCyber`, `TaxCompliance`, `RegulatoryCheck`, `ConversationStart`

### Reporting Agent

Compiles findings into structured executive summaries.

| Section | Content |
|---|---|
| **Overview** | Contract type, parties, value, term |
| **Key Terms Table** | Extracted terms in tabular format |
| **Risk Assessment** | Traffic-light indicators (🔴🟡🟢) from Legal & Compliance |
| **Recommendations** | Must Fix (blocking) → Should Fix (risk reduction) → Consider (improvement) |
| **Next Steps** | Action items with owners and deadlines |

**Topics:** `TermExtraction`, `ExecutiveSummary`, `ConversationStart`

### Portfolio Intelligence Agent

Queries a Microsoft Fabric lakehouse for data-grounded portfolio analytics.

| Capability | Details |
|---|---|
| **Benchmarking** | Payment terms, liability caps, auto-renewal rates, contract values vs. similar types & vendor tiers; percentile rankings |
| **Vendor Performance** | Compliance scores, tier classification (Strategic/Preferred/Standard/Probationary), incident history |
| **Spend Analytics** | Budget vs. actual variance, cost trends by vendor/department/category, YoY analysis |
| **Renewal Tracking** | Expiring contracts at 30/60/90-day horizons, auto-renewal notice deadlines |
| **Compliance Trends** | Incident frequency & severity by vendor, type, and department |

**Topics:** `PortfolioBenchmark`, `SpendAnalytics`, `RenewalTracker`, `ConversationStart`

## Contract Redline Tool

A Python FastAPI microservice that applies tracked changes to Word documents stored in SharePoint.

### How It Works

```mermaid
graph TD
    A["POST /api/redline"] --> B["Download .docx from SharePoint<br/>(Graph API)"]
    B --> C["Apply tracked changes via OpenXML<br/>(w:del / w:ins elements)"]
    C --> D["Add Word comments with risk-rated rationale<br/>(🔴 Major, 🟡 Moderate, 🟢 Minor)"]
    D --> E["Upload redlined .docx<br/>back to SharePoint"]
    E --> F["Return results with<br/>SharePoint URL"]
```

### API Reference

#### `POST /api/redline`

**Headers:** `X-API-Key: <your-api-key>`

**Request Body:**
```json
{
  "document_url": "https://contoso.sharepoint.com/sites/Procurement/Shared Documents/contract.docx",
  "recommendations": [
    {
      "original_text": "Net 45 days",
      "replacement_text": "Net 30 days",
      "rationale": "Policy requires Net 30 for contracts under $500K",
      "risk_level": "major",
      "section": "Payment Terms"
    }
  ],
  "author": "Contract Review Agent",
  "output_filename": "contract-redlined",
  "output_folder_url": "https://contoso.sharepoint.com/sites/Procurement/Shared Documents/Redlined/"
}
```

**Response:**
```json
{
  "status": "success",
  "output_url": "https://contoso.sharepoint.com/...",
  "changes_applied": 1,
  "changes_failed": 0,
  "comments_added": 1,
  "results": [
    {
      "original_text": "Net 45 days",
      "replacement_text": "Net 30 days",
      "applied": true,
      "comment_added": true,
      "error": ""
    }
  ],
  "summary": "Applied 1/1 tracked changes with 1 rationale comments."
}
```

#### `GET /health`

Returns `{"status": "healthy", "version": "1.0.0", "service": "Contract Redline Tool"}`.

### Supported URL Formats

- **Direct SharePoint URLs:** `https://contoso.sharepoint.com/sites/Site/Shared Documents/file.docx`
- **Sharing links:** `https://contoso.sharepoint.com/:w:/s/Site/EaBc...?e=token` (resolved via Graph `/shares` API)

### Local Development

```bash
cd ContractRedlineTool
python -m venv .venv
.venv/Scripts/activate      # Windows
# source .venv/bin/activate  # Linux/macOS

pip install -r requirements.txt
cp .env.example .env         # Configure Azure credentials
python -m uvicorn app.main:app --reload --port 8000
```

**Environment Variables (`.env`):**

| Variable | Description | Required |
|---|---|---|
| `AZURE_TENANT_ID` | Entra ID tenant ID | For local dev |
| `AZURE_CLIENT_ID` | App registration client ID | For local dev |
| `AZURE_CLIENT_SECRET` | App registration secret | For local dev (if not using cert) |
| `AZURE_CLIENT_CERTIFICATE_PATH` | Path to `.pfx` certificate file | For local dev (if secrets disabled) |
| `AZURE_CLIENT_CERTIFICATE_PASSWORD` | Certificate password | If cert is password-protected |
| `API_KEY` | API key for `X-API-Key` header | Yes (empty string disables auth) |
| `TEMP_DIR` | Temp directory for file processing | No (default: `/tmp/redline`) |

In production (Azure App Service), authentication uses the system-assigned Managed Identity via `DefaultAzureCredential` — no `AZURE_TENANT_ID` or `AZURE_CLIENT_ID` needed.

### Running Tests

```bash
cd ContractRedlineTool
pytest                                  # Full suite
pytest tests/test_redline_engine.py     # Redline engine tests
pytest tests/test_api.py                # API endpoint tests
pytest -k "test_apply_single_change"    # Single test
```

Tests create real `.docx` files using `tmp_path` and verify OpenXML output. Graph API calls are mocked with `unittest.mock.patch`.

### Docker

```bash
docker build -t contract-redline-tool .
docker run -p 8000:8000 --env-file .env contract-redline-tool
```

### Deploy to Azure App Service

**Infrastructure (Bicep):**

```bash
az deployment group create \
  --resource-group rg-contract-agent \
  --template-file deploy/bicep/main.bicep \
  --parameters namePrefix=contract-redline
```

This creates a Linux App Service (Python 3.11, B1 SKU) with system-assigned Managed Identity, HTTPS-only, TLS 1.2, and FTP disabled.

**Code deployment:**

```bash
cd ContractRedlineTool
az webapp up --name <app-name> --resource-group <rg-name> --runtime "PYTHON:3.11" --sku B1
```

**Post-deployment — Grant Graph API permissions to Managed Identity:**

The Managed Identity needs `Sites.ReadWrite.All` and `Files.ReadWrite.All` application permissions on Microsoft Graph. Use `az rest` to assign app roles (requires Global Administrator or Privileged Role Administrator):

```powershell
# Get the Managed Identity principal ID from Bicep output or:
az webapp identity show --name <app-name> --resource-group <rg-name> --query principalId -o tsv

# Get the Graph service principal object ID:
az ad sp show --id 00000003-0000-0000-c000-000000000000 --query id -o tsv

# Look up correct app role IDs:
az ad sp show --id 00000003-0000-0000-c000-000000000000 \
  --query "appRoles[?value=='Sites.ReadWrite.All'].id" -o tsv

# Grant via az rest (repeat for each permission):
$body = @{
  principalId = "<managed-identity-principal-id>"
  resourceId  = "<graph-sp-object-id>"
  appRoleId   = "<app-role-id>"
} | ConvertTo-Json
$body | Out-File grant.json -Encoding utf8
az rest --method POST \
  --uri "https://graph.microsoft.com/v1.0/servicePrincipals/<graph-sp-object-id>/appRoleAssignments" \
  --headers "Content-Type=application/json" \
  --body @grant.json
```

**Configure app settings:**

```bash
az webapp config appsettings set --name <app-name> --resource-group <rg-name> \
  --settings API_KEY=<your-key> TEMP_DIR=/tmp/redline DEBUG=false
```

## Knowledge Sources

The orchestrator agent references four SharePoint-linked knowledge sources (in `ContractAgent/knowledge/`) for RAG-style grounding. These connect to:

- **Corporate Procurement Policy** — Approval thresholds, mandatory clauses, prohibited terms
- **Legal Review Playbook** — 26-item clause checklist, risk classification matrix, approved alternative language
- **Compliance Checklist** — Tax, insurance, cybersecurity, regulatory requirements
- **Contract Templates** — NDA and Vendor Services Agreement templates

Agents must cite specific policy sections. If guidance isn't found in knowledge sources, agents respond with: *"I don't have specific guidance for that in Contoso's policies. Please consult the Legal or Compliance team directly."*

## Fabric Lakehouse Setup

The Portfolio Intelligence Agent queries a Microsoft Fabric lakehouse. Sample data is in `documentation/sample-data/fabric/`:

| Table | Rows | Description |
|---|---|---|
| `contracts` | 54 | Master contract records (type, value, status, expiration, payment terms, risk rating) |
| `contract_clauses` | 288 | Clause-level detail (clause type, compliance, deviation type, risk score) |
| `vendors` | 20 | Vendor master (tier, compliance score, country, active contracts) |
| `compliance_incidents` | 34 | Historical incidents (type, severity, financial impact) |
| `spend_actuals` | 195 | Budget vs. actual spend by quarter (variance, department, category) |

**Relationships:** `contracts.vendor_id` → `vendors.vendor_id`; `contracts.contract_id` → `contract_clauses`, `compliance_incidents`, `spend_actuals`.

### Setup Steps

1. Create a lakehouse (`ContractPortfolioLH`) in a Fabric workspace (requires F2+ capacity)
2. Upload the five CSVs and load as Delta tables
3. Create a Fabric Data Agent, select all five tables
4. Add data agent instructions (schema descriptions and join guidance)
5. Add example SQL queries for common questions
6. Publish and connect to the orchestrator in Copilot Studio

See [`.github/copilot-instructions.md`](.github/copilot-instructions.md) for detailed step-by-step instructions including example queries and SQL.

## Personas

Four stakeholder personas are defined in `persona/` for scenario testing and demo flows:

| Persona | Role | Primary Agents |
|---|---|---|
| Laila Tuilagi | Senior Procurement Officer | Intake, Portfolio Intelligence, Redline Tool |
| Kwame Osei-Mensah | Associate General Counsel | Legal Review, Portfolio Intelligence, Redline Tool |
| Elena Vasquez | Chief Compliance Officer | Compliance & Risk, Portfolio Intelligence |
| James Chen | VP of Finance | Portfolio Intelligence, Reporting |

## Sample Data

The `documentation/sample-data/` directory contains test contracts and policy documents:

| File | Purpose |
|---|---|
| `sample-contract-compliant.md` | Fully compliant vendor agreement (baseline) |
| `sample-contract-high-risk.md` | Contract with prohibited terms (unlimited liability, etc.) |
| `sample-contract-expired-terms.md` | Contract with outdated certifications and terms |
| `sample-contract-missing-clauses.md` | Contract missing critical required clauses |
| `corporate-procurement-policy.md` | Contoso procurement policy with approval thresholds |
| `legal-review-playbook.md` | 26-item clause checklist with risk matrix |
| `compliance-checklist.md` | Multi-domain compliance requirements |
| `contract-template-nda.md` | Standard NDA template |
| `contract-template-vendor-agreement.md` | Standard vendor agreement template |
| `test-scenarios.md` | End-to-end test scenarios for all agent flows |

## Conventions

- **Risk Classification:** Three-tier system used across all agents — Major (🔴), Moderate (🟡), Minor (🟢). Maps to the `RiskLevel` enum in the Redline Tool.
- **Policy Grounding:** All agents cite specific policy/playbook sections. No general model knowledge for contract-specific guidance.
- **Agent Files:** All use `.mcs.yml` extension. Connected agents use `AgentDialog` kind with `OnToolSelected` triggers.
- **Orchestrator Schema:** `cr57c_agentqf4ruA` — appears in knowledge source filenames and settings.
- **Redline Tool Auth:** API key via `X-API-Key` header (empty key disables validation in dev). Production uses Managed Identity for Graph API.
- **Graph API Permissions:** `Sites.ReadWrite.All` and `Files.ReadWrite.All` (application type) required for SharePoint operations.

## Technology Stack

| Component | Technology |
|---|---|
| Agent Platform | Microsoft Copilot Studio |
| Agent Model | opus4-1 |
| Knowledge Grounding | SharePoint + Copilot Studio RAG |
| Portfolio Analytics | Microsoft Fabric Lakehouse + Data Agent |
| Redline Microservice | Python 3.11, FastAPI, uvicorn, gunicorn |
| Document Manipulation | python-docx, lxml (OpenXML) |
| SharePoint Integration | Microsoft Graph API, azure-identity, httpx |
| Infrastructure as Code | Bicep |
| Hosting | Azure App Service (Linux, B1 SKU) |
| Authentication | System-assigned Managed Identity (prod), Certificate/Secret (dev) |
| Testing | pytest, pytest-asyncio, FastAPI TestClient |
