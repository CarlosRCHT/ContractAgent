# Contract Redline Agent (Azure AI Foundry)

A Foundry Agent Service agent that applies tracked changes and reviewer
comments to Word contracts on SharePoint. Designed to be added as a connected
agent in Copilot Studio alongside the existing FastAPI-based
`ContractRedlineTool` (which is left untouched).

## What's different from `ContractRedlineTool`

| Aspect | ContractRedlineTool (FastAPI) | ContractRedlineAgent (this) |
|---|---|---|
| Hosting | App Service / container | Foundry Agent Service (Code Interpreter) |
| Entry point | `POST /api/redline` | Agent invocation from Copilot Studio |
| Input shape | Strict JSON | Free-form payload, normalized by the agent |
| Edit granularity | Sentence-level replace | **Word-level** tracked edits |
| Comment scope | Around the replaced span | **Whole sentence / paragraph** |
| Coherence check | None | LLM checks surrounding context, **adjusts** wording on failure |
| Graph auth | Client secret / cert | **Managed identity** (via Logic App tools) |

## Architecture

```
Copilot Studio
   │ (connected agent)
   ▼
Foundry Agent: contract-redline-agent
   ├── Logic App tool: download_contract           (system-assigned MI → Graph)
   ├── Logic App tool: upload_redlined_contract    (system-assigned MI → Graph)
   └── Code Interpreter   (runs redline_core.py / docx_text.py / schemas.py)
```

## Layout

- `agent/code_files/` — Python modules uploaded as agent files; imported from
  Code Interpreter at run time.
- `agent/instructions.md` — system prompt that drives the orchestration.
- `agent/definition.py` — registers / updates the agent in your Foundry project.
- `tools/` — OpenAPI specs the agent uses to register the two Logic App tools.
- `deploy/` — Bicep + Logic App workflow JSON.
- `scripts/` — `deploy_agent.py` (idempotent), `smoke_test.py` (no Foundry
  needed), `grant_graph_permissions.ps1`.
- `tests/` — pytest suite for the diff engine and helpers.

## Deploy

1. **Provision infrastructure** (Logic Apps + MI + Graph role assignments):
   ```powershell
   az deployment group create `
     --resource-group rg-contract-agent `
     --template-file deploy/bicep/main.bicep `
     --parameters namePrefix=contract-redline
   ```
2. **Grant Microsoft Graph application permissions** to the Logic App MIs
   (requires Privileged Role Administrator or Global Administrator):
   ```powershell
   ./scripts/grant_graph_permissions.ps1 -ResourceGroupName rg-contract-agent
   ```
   Then capture the Logic App invoke URLs and put them in `.env`:
   ```powershell
   az rest --method post `
     --uri "https://management.azure.com/subscriptions/<sub>/resourceGroups/rg-contract-agent/providers/Microsoft.Logic/workflows/contract-redline-download/triggers/manual/listCallbackUrl?api-version=2016-06-01" `
     --query value -o tsv
   ```
3. **Register / update the Foundry agent**:
   ```powershell
   az login
   pip install -r requirements.txt
   python scripts/deploy_agent.py
   ```
4. **Add to Copilot Studio**: in the `ContractAgent` orchestrator, add a new
   connected agent → choose **Azure AI Foundry agent** → select
   `contract-redline-agent`.

## Local smoke test

Runs the redline pipeline on a fixture .docx with mocked Graph calls — no
Azure resources required:

```powershell
pip install -r requirements.txt
pytest
python scripts/smoke_test.py
```

See `Documentation/redline-agent.md` for design details.
