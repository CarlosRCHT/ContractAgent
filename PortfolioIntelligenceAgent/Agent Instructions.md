This data source contains Contoso's enterprise contract portfolio data across five tables:

- contracts: Master contract records. Key fields: contract_id, vendor_id, contract_type, total_value, annual_value, status, effective_date, expiration_date, payment_terms_days, auto_renewal, risk_rating, department.

- contract_clauses: Clause-level records linked to contracts. Key fields: contract_id, clause_type, standard_compliant (boolean), deviation_type (Major/Moderate/Minor/None), risk_score (1-10), review_status, recommendation.

- vendors: Vendor records with tier classification. Key fields: vendor_id, vendor_name, vendor_type (Strategic/Preferred/Standard/Probationary), compliance_score (0-100), country, total_contract_value, active_contracts_count.

- compliance_incidents: Historical compliance incidents. Key fields: contract_id, vendor_id, incident_type, severity (High/Medium/Low), detected_date, resolved_date, financial_impact.

- spend_actuals: Quarterly spend records. Key fields: contract_id, vendor_id, fiscal_year, fiscal_quarter, budgeted_amount, actual_amount, variance_pct, spend_category, department.

IMPORTANT — EXACT VALUES FOR contract_type column (use these exactly in SQL WHERE clauses, never abbreviations or synonyms):
- "Consulting Agreement"
- "Software License"
- "Supply Agreement"
- "Staffing Agreement"
- "Maintenance Agreement"
- "Professional Services"
- "Master Service Agreement"
- "Statement of Work"
- "Lease Agreement"
- "Vendor Services Agreement"

Common synonyms to map: "VSA" or "Vendor Agreement" or "Vendor Service Agreement" → use "Vendor Services Agreement". "SOW" → use "Statement of Work". "MSA" → use "Master Service Agreement".

IMPORTANT — EXACT VALUES FOR clause_type column in contract_clauses (use these exactly):
Payment Terms, Liability Limitation, Auto-Renewal, Insurance - General Liability, Insurance - Professional Liability, Insurance - Cyber Liability, Insurance - Auto Liability, Insurance - Additional Insured, Cybersecurity, Confidentiality, Termination, Warranty, Indemnification, Force Majeure, IP Ownership, Governing Law, Dispute Resolution, Data Breach Notification, Contract Term, Subcontracting, Price Escalation, Amendment, Data Residency, Certifications, Regulatory Compliance, Pre-existing IP License, Confidentiality - Return Period.

Common synonyms to map: "Liability Cap" → use "Liability Limitation". "Fee Escalation" → use "Price Escalation".

IMPORTANT: Contracts are identified by contract_id, NOT by agreement numbers. When users reference an agreement number like "AC-MSA-2021-0156", search the title or clause_text_summary fields, or match by vendor name + contract type.

Use contracts.vendor_id to join with vendors.vendor_id. Use contracts.contract_id to join with contract_clauses, compliance_incidents, and spend_actuals.

When answering benchmarking questions, provide averages, medians, and percentile context. When analyzing spend, compute variance as (actual - budgeted) / budgeted * 100. Vendor risk ratings map to tiers: Strategic > Preferred > Standard > Probationary.