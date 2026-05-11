# Contract Redline Agent — Design Notes

The Contract Redline Agent is an **Azure AI Foundry Agent Service** agent that
sits beside the existing FastAPI-based `Azure/ContractRedlineTool`. The two
implementations share an OpenXML approach to tracked changes but differ in
hosting model, edit granularity, and how recommendations are validated.

## Why a Foundry agent

The redline workflow benefits from being expressed as an *agent* rather than a
fixed HTTP endpoint:

- **Free-form input.** The Fabric data agent and reasoning agents emit
  recommendations in whatever shape best fits their reasoning; the Foundry
  agent normalizes them into a strict internal schema.
- **In-context coherence checks.** Each proposed change is validated against
  the surrounding paragraphs by the same model that orchestrates the run. If
  the wording would break grammar, contradict an adjacent clause, or leave
  the surrounding text incoherent, the agent rewrites it before applying.
- **Connected-agent integration.** Copilot Studio can add the agent as a
  connected sub-agent without standing up an OpenAPI front door.

## Edit granularity

Where `ContractRedlineTool` replaces a whole matched span (sentence-level),
this agent runs `difflib.SequenceMatcher` over a lossless tokenizer:

```python
re.findall(r"\s+|\w+|[^\w\s]", text)
```

Only the words that actually change are wrapped in `<w:del>` / `<w:ins>`.
Unchanged words remain plain runs. This keeps reviewer focus on the actual
edit and, in long sentences, dramatically reduces the visual noise.

## Comment scope

A single `<w:comment>` per change brackets the **entire affected sentence**
via `<w:commentRangeStart/End>`. If the change crosses sentence boundaries
inside a paragraph, the bracket falls back to the whole paragraph. The
comment body is always:

```
<risk emoji> <riskLevel>: <rationale>
```

with an "Adjusted from original recommendation: ..." line appended when the
agent rewrote the wording during the coherence check.

## Microsoft Graph access

Code Interpreter cannot use the Foundry resource's managed identity directly,
so two **Consumption Logic Apps** are deployed alongside the agent:

| Logic App | Purpose |
|---|---|
| `contract-redline-download` | Resolves a SharePoint share URL via Graph `/shares/{token}/driveItem`, returns base64 bytes + drive/parent IDs. |
| `contract-redline-upload` | PUTs base64 bytes to a Graph drive folder, returns the new web URL. |

Each has a system-assigned managed identity that holds Graph application
permissions. The Foundry agent calls them via OpenAPI tool definitions
(`tools/*.openapi.json`).

## Files

| Path | Role |
|---|---|
| `agent/code_files/redline_core.py` | Tokenizer, `word_diff`, `RedlineEngine` |
| `agent/code_files/docx_text.py` | Sentence splitter, anchor span logic |
| `agent/code_files/schemas.py` | Pydantic models for normalized payloads |
| `agent/instructions.md` | Agent system prompt — orchestration policy |
| `tools/*.openapi.json` | OpenAPI specs registered as Foundry tools |
| `deploy/bicep/main.bicep` | Logic Apps + system-assigned MIs |
| `deploy/logicapps/*.json` | Workflow definitions |
| `scripts/deploy_agent.py` | Idempotent agent registration |
| `scripts/smoke_test.py` | Local engine verification |
| `scripts/grant_graph_permissions.ps1` | Admin-consent helper |

## Coherence-check policy

The agent applies an **adjust-then-apply** policy. Every recommendation is
applied — the only failure modes are:

1. `originalText` not found in the document → return an `error` for that
   item without applying.
2. The proposed wording would directly contradict an adjacent clause that
   cannot be reconciled by rewording → return an `error`.

In all other cases, if the wording is incoherent, the agent rewrites it,
applies the rewritten version, and writes an "Adjusted from original
recommendation" note to the comment.
