# Contract Redline Tool

A FastAPI service that applies tracked changes and rationale comments to Word contracts stored in SharePoint, driven by AI agent recommendations. Designed as a Copilot Studio plugin for the Contract Agent multi-agent solution.

## Quick Start (Local Development)

```bash
cd ContractRedlineTool

# Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # Linux/macOS

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your Azure AD / SharePoint credentials

# Run the server
uvicorn app.main:app --reload --port 8000
```

The API is now available at `http://localhost:8000`. Interactive docs are at [`/docs`](http://localhost:8000/docs).

## API Reference

### `POST /api/redline`

Applies tracked changes to a SharePoint Word document and returns the URL of the redlined copy.

**Headers**

| Header      | Description                          |
|-------------|--------------------------------------|
| `X-API-Key` | API key (required if `API_KEY` is set) |

**Request Body**

```json
{
  "documentUrl": "https://contoso.sharepoint.com/sites/contracts/Shared Documents/NDA.docx",
  "recommendations": [
    {
      "originalText": "unlimited liability",
      "replacementText": "liability not to exceed the total contract value",
      "rationale": "Prohibited term per procurement policy §4.2",
      "riskLevel": "major",
      "section": "Limitation of Liability"
    }
  ],
  "author": "Contract Review Agent",
  "outputFilename": ""
}
```

**Response**

```json
{
  "status": "success",
  "outputUrl": "https://contoso.sharepoint.com/sites/contracts/Shared Documents/NDA_redlined.docx",
  "changesApplied": 1,
  "changesFailed": 0,
  "commentsAdded": 1,
  "results": [
    {
      "originalText": "unlimited liability",
      "replacementText": "liability not to exceed the total contract value",
      "applied": true,
      "commentAdded": true,
      "error": ""
    }
  ],
  "summary": "Applied 1/1 tracked changes with 1 rationale comments. "
}
```

### `GET /health`

Returns `{"status": "healthy", "version": "1.0.0", "service": "Contract Redline Tool"}`.

### `POST /api/extract-text`

Downloads a Word document from SharePoint and returns its plain text content.

**Request Body**

```json
{
  "documentUrl": "https://contoso.sharepoint.com/sites/contracts/Shared Documents/NDA.docx"
}
```

**Response**

```json
{
  "status": "success",
  "filename": "NDA.docx",
  "text": "VENDOR SERVICES AGREEMENT\nBetween Contoso and ...",
  "pageCount": 3,
  "error": ""
}
```

## Deployment to Azure App Service

### Option 1: Bicep (Infrastructure as Code)

```bash
az deployment group create \
  --resource-group rg-contract-agent \
  --template-file deploy/bicep/main.bicep \
  --parameters namePrefix=contract-redline

# Deploy application code
az webapp deploy --resource-group rg-contract-agent \
  --name contract-redline-app --src-path .
```

### Option 2: Docker

```bash
docker build -t contract-redline-tool .
docker run -p 8000:8000 --env-file .env contract-redline-tool
```

Then push the image to Azure Container Registry and configure the App Service to pull from it.

### Post-Deployment

1. Set environment variables (App Settings) in the Azure Portal or via CLI.
2. Grant the App Service managed identity **Sites.ReadWrite.All** and **Files.ReadWrite.All** Graph API permissions.
3. Remove `AZURE_CLIENT_SECRET` once managed identity is configured.

## Environment Variables

| Variable               | Required | Description                                              |
|------------------------|----------|----------------------------------------------------------|
| `AZURE_TENANT_ID`     | Yes      | Microsoft Entra ID tenant ID                             |
| `AZURE_CLIENT_ID`     | Yes      | App registration client ID with Graph API permissions    |
| `AZURE_CLIENT_SECRET` | No*      | Client secret (omit when using Managed Identity)         |
| `SHAREPOINT_SITE_ID`  | No       | Pre-resolved SharePoint site ID (skips Graph lookup)     |
| `SHAREPOINT_DRIVE_ID` | No       | Pre-resolved drive ID (skips Graph lookup)               |
| `API_KEY`             | Yes      | API key for authenticating callers (e.g., Copilot Studio)|
| `APP_NAME`            | No       | Display name (default: `Contract Redline Tool`)          |
| `DEBUG`               | No       | Enable debug logging (default: `false`)                  |
| `TEMP_DIR`            | No       | Temp directory for file processing (default: `/tmp/redline`) |
| `DEFAULT_AUTHOR`      | No       | Default author for tracked changes (default: `Contract Review Agent`) |

\* Required for local development; use Managed Identity in production.

## Copilot Studio Integration

This tool is designed to be called from a Copilot Studio agent as a custom connector / plugin:

1. **OpenAPI Spec** — The FastAPI app auto-generates an OpenAPI 3.0 spec at `/docs` and `/openapi.json`. Use this URL when creating a custom connector in Copilot Studio.
2. **Authentication** — Configure API Key authentication with header name `X-API-Key`.
3. **Custom Connector** — In Copilot Studio, add a new connector action pointing to your deployed App Service URL (e.g., `https://contract-redline-app.azurewebsites.net`).
4. **Topic Flow** — The agent collects the document URL and AI-generated recommendations, calls `POST /api/redline`, and presents the `output_url` and `summary` to the user.

See [`documentation/redline-tool.md`](../documentation/redline-tool.md) for the full technical reference.

## Testing

```bash
pytest tests/ -v
```

## License

Internal use — see repository root for license details.
