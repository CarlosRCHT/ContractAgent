 # Question
 Benchmark a maintenance contract's payment terms and liability against the portfolio

# SQL Query
``` sql
SELECT
     c.contract_id,
     c.vendor_name,
     c.annual_value,
     c.payment_terms_days,
     c.auto_renewal,
     cl_liab.clause_text_summary AS liability_clause,
     cl_warr.clause_text_summary AS warranty_clause
 FROM contracts c
 LEFT JOIN contract_clauses cl_liab
     ON c.contract_id = cl_liab.contract_id AND cl_liab.clause_type = 'Liability Limitation'
 LEFT JOIN contract_clauses cl_warr
     ON c.contract_id = cl_warr.contract_id AND cl_warr.clause_type = 'Warranty'
 WHERE c.contract_type = 'Maintenance Agreement'
 ORDER BY c.annual_value DESC