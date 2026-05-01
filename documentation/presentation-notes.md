# Customer Presentation: Contoso Contract Management Agent — Slide Notes

---

## Slide 1: The Problem

**Title:** *Contract Reviews Take 4–5 Months — And It's Getting Worse*

**Talking points:**

- Contoso's contract lifecycle averages **4–5 months** from initiation to execution
- Bottlenecks are in **drafting, review, and dispatch** — not data entry
- Contracts live across **5+ disconnected systems** (SharePoint, CRM, ERP, Procurement Platform, Document Management) with no single source of truth
- **~30% procurement staff attrition** while contract volume keeps growing
- Contracts "go dark" — expired discounts, missed obligations, lost revenue
- Review teams (legal, tax, insurance, cybersecurity) work in **silos** with manual playbook comparison and no automated deviation flagging

**Visual suggestion:** Before/after process flow diagram. Show the current manual process with red-highlighted pain points at the drafting, review, and dispatch stages.

---

## Slide 2: The Solution — Multi-Agent Contract Review

**Title:** *AI-Powered Contract Lifecycle Automation on Microsoft Copilot Studio*

**Talking points:**

- **Hub-and-spoke architecture** — one orchestrator routes work to five specialized agents
- **Pipeline:** Intake → Legal Review → Compliance Check → Reporting (+ on-demand Portfolio Intelligence)
- Each agent is **policy-grounded** — every recommendation cites a specific policy section, template clause, or playbook item. No hallucination or tribal knowledge.
- **Human-in-the-loop** at every stage — agents flag and recommend, humans decide
- Built entirely on **Microsoft Copilot Studio** with connected agents, no custom LLM infra needed

| Agent | What It Does |
|---|---|
| **Intake** | Classifies contract type (5 categories), assigns urgency tier (7/14/30-day SLA) |
| **Legal Review** | 26-item playbook comparison, 3-tier risk classification (🔴🟡🟢) |
| **Compliance** | Tax, insurance, cybersecurity, regulatory checks with traffic-light scoring |
| **Reporting** | Extracts key terms, generates executive summary with Must Fix / Should Fix / Consider |
| **Portfolio Intelligence** | Benchmarks against historical portfolio via Microsoft Fabric lakehouse |

**Visual suggestion:** The hub-and-spoke architecture diagram from the design doc, emphasizing the sequential pipeline with the orchestrator at center.

---

## Slide 3: Document Automation — The Redline Tool

**Title:** *From AI Findings to Tracked Changes in Word — Automatically*

**Talking points:**

- A **Python FastAPI microservice** bridges the gap between agent analysis and document markup
- Takes AI recommendations → downloads the `.docx` from SharePoint → applies **native Word tracked changes** (`<w:ins>` / `<w:del>`) → adds **risk-rated comments** (🔴 Major, 🟡 Moderate, 🟢 Minor) → uploads back to SharePoint
- Reviewers see changes in **Word's native Track Changes UI** — no new tool to learn
- Deployed to **Azure App Service** with Managed Identity for secure Graph API access
- Each comment cites the **specific policy section** driving the recommendation

**Visual suggestion:** A before/after screenshot of a Word document — showing original text on the left and the redlined version with tracked changes and comment balloons on the right. Alternatively, the request → response API flow diagram.

---

## Slide 4: Portfolio Intelligence — Data-Driven Decisions

**Title:** *Benchmark Every Contract Against Your Entire Portfolio*

**Talking points:**

- **Microsoft Fabric lakehouse** with 5 Delta tables: contracts (54), clauses (288), vendors (20), compliance incidents (34), spend actuals (195 quarterly records)
- Natural-language queries via **Fabric Data Agent** connected to Copilot Studio
- Capabilities:
  - "What contracts are expiring in the next 90 days?" — renewal risk tracking
  - "Show spend variance by vendor for FY2025" — budget vs. actual analysis
  - "Which vendors have the most compliance incidents?" — vendor risk profiling
  - Benchmark payment terms, contract value, and risk by type and vendor tier
- Turns portfolio data into **actionable context during live reviews** — not just after-the-fact reporting

**Visual suggestion:** A sample natural-language query with the structured data response it produces, or a dashboard mockup showing spend variance and expiring contracts.

---

## Slide 5: Business Impact & Target Outcomes

**Title:** *From 4–5 Months to ~1 Month*

**Talking points:**

- **Target:** Reduce contract cycle time from 4–5 months to **~1 month**
- Key improvements:
  - **Classification in < 30 seconds** (vs. manual triage)
  - **Automated review in < 5 minutes per domain** (vs. days of manual playbook comparison)
  - **Word markup in < 2 minutes** (vs. hours of manual redlining)
  - **Concurrent processing** of 10+ contracts (vs. sequential manual queues)
- **Governance built-in:** Audit trail, RBAC, data residency compliance, policy-grounded outputs, human-in-the-loop
- **Composable architecture:** Add new agents (e.g., Financial Review) without modifying existing ones
- **Security:** All data stays within the Azure tenant, encryption at rest/in-transit, no data used for model training

**Visual suggestion:** A side-by-side timeline comparison — current 4–5 month waterfall vs. the compressed ~1 month AI-assisted flow. Include the specific SLA targets for each stage.

---

## Slide 6 (Optional): Demo & Next Steps

**Title:** *See It in Action*

**Talking points:**

- Live demo flow: Submit a high-risk vendor agreement → watch intake classify it as "Critical 7-day" → legal review flags prohibited terms → compliance scores it Red → reporting generates executive summary → redline tool produces the marked-up Word doc
- **Sample contracts available** in the repo: compliant, high-risk, missing-clauses, and expired-terms variants for different demo scenarios
- **Next steps:**
  - Integration with Workflow Management System for intake tracking
  - ERP/CRM master data connections
  - Configurable risk thresholds and classification rules
  - Production rollout with private endpoints and full RBAC

**Visual suggestion:** Screenshot of the Copilot Studio chat interface with a real interaction, or a short embedded video/GIF of the end-to-end flow.

---

## General Presentation Tips

- **Lead with the pain** (Slide 1) — the customer's procurement team already lives this problem daily
- **Slide 3 (Redline Tool) is the "wow" moment** — executives understand tracked changes in Word; it makes the AI output tangible
- **Keep the Fabric slide** if the audience includes finance/procurement leadership; drop it for a purely legal audience
- Use the **four personas** in the `persona/` folder (Elena/Procurement, James/Legal, Kwame/Compliance, Laila/Finance) to frame each agent's value from a stakeholder perspective
