<#
.SYNOPSIS
    Deploys the Contract Redline Tool to Azure App Service.

.DESCRIPTION
    Zips the application source and deploys it to the Azure App Service
    using az webapp deploy. Runs pip install on the server via
    SCM_DO_BUILD_DURING_DEPLOYMENT.

.PARAMETER ResourceGroup
    Azure resource group name. Default: EXP-TOR-SDBX-RG

.PARAMETER AppName
    Azure App Service name. Default: contract-redline-app

.PARAMETER SkipTests
    Skip running pytest before deploying.

.EXAMPLE
    .\deploy.ps1
    .\deploy.ps1 -SkipTests
    .\deploy.ps1 -ResourceGroup my-rg -AppName my-app
#>
param(
    [string]$ResourceGroup = "EXP-TOR-SDBX-RG",
    [string]$AppName = "contract-redline-app",
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $ScriptDir

try {
    # --- Pre-flight checks ---
    Write-Host "=== Contract Redline Tool Deployment ===" -ForegroundColor Cyan

    # Verify az CLI is logged in
    $account = az account show --query "name" -o tsv 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Not logged in to Azure CLI. Run 'az login' first."
        exit 1
    }
    Write-Host "Subscription: $account" -ForegroundColor Gray

    # Verify the app exists
    $appState = az webapp show --resource-group $ResourceGroup --name $AppName --query "state" -o tsv 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Error "App '$AppName' not found in resource group '$ResourceGroup'. Check the name and subscription."
        exit 1
    }
    Write-Host "App Service:  $AppName ($appState)" -ForegroundColor Gray

    # --- Run tests ---
    if (-not $SkipTests) {
        Write-Host "`n--- Running tests ---" -ForegroundColor Yellow
        & .\.venv\Scripts\python.exe -m pytest -q
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Tests failed. Fix them before deploying, or use -SkipTests to bypass."
            exit 1
        }
        Write-Host "Tests passed." -ForegroundColor Green
    }

    # --- Build zip package ---
    Write-Host "`n--- Building deployment package ---" -ForegroundColor Yellow
    $zipPath = Join-Path $env:TEMP "contract-redline-deploy.zip"
    if (Test-Path $zipPath) { Remove-Item $zipPath -Force }

    # Include only what the app needs
    $includes = @(
        "app/**",
        "requirements.txt",
        "startup.sh"
    )

    # Use a staging folder to assemble the package
    $stagingDir = Join-Path $env:TEMP "contract-redline-staging"
    if (Test-Path $stagingDir) { Remove-Item $stagingDir -Recurse -Force }
    New-Item -ItemType Directory -Path $stagingDir | Out-Null

    foreach ($pattern in $includes) {
        $items = Get-ChildItem -Path $pattern -Recurse -ErrorAction SilentlyContinue
        foreach ($item in $items) {
            $relativePath = $item.FullName.Substring((Get-Location).Path.Length + 1)
            $destPath = Join-Path $stagingDir $relativePath
            $destDir = Split-Path -Parent $destPath
            if (-not (Test-Path $destDir)) {
                New-Item -ItemType Directory -Path $destDir -Force | Out-Null
            }
            Copy-Item $item.FullName -Destination $destPath
        }
    }

    # Also copy top-level files explicitly
    foreach ($file in @("requirements.txt", "startup.sh")) {
        Copy-Item $file -Destination (Join-Path $stagingDir $file) -ErrorAction SilentlyContinue
    }

    Compress-Archive -Path "$stagingDir\*" -DestinationPath $zipPath -Force
    Remove-Item $stagingDir -Recurse -Force
    $sizeMB = [math]::Round((Get-Item $zipPath).Length / 1MB, 2)
    Write-Host "Package: $zipPath ($sizeMB MB)" -ForegroundColor Gray

    # --- Deploy ---
    Write-Host "`n--- Deploying to $AppName ---" -ForegroundColor Yellow
    az webapp deploy `
        --resource-group $ResourceGroup `
        --name $AppName `
        --src-path $zipPath `
        --type zip `
        --async false 2>&1 | Write-Host

    if ($LASTEXITCODE -ne 0) {
        Write-Error "Deployment failed."
        exit 1
    }

    # --- Verify ---
    Write-Host "`n--- Verifying deployment ---" -ForegroundColor Yellow
    $healthUrl = "https://$AppName.azurewebsites.net/health"
    $maxRetries = 6
    $retryDelay = 10

    for ($i = 1; $i -le $maxRetries; $i++) {
        try {
            $response = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 10 -ErrorAction Stop
            if ($response.status -eq "healthy") {
                Write-Host "`nDeployment successful!" -ForegroundColor Green
                Write-Host "  Health: $healthUrl" -ForegroundColor Gray
                Write-Host "  API:    https://$AppName.azurewebsites.net/api/redline" -ForegroundColor Gray
                exit 0
            }
        } catch {
            Write-Host "  Waiting for app to start (attempt $i/$maxRetries)..." -ForegroundColor Gray
            Start-Sleep -Seconds $retryDelay
        }
    }

    Write-Warning "App deployed but health check did not return 'healthy' after $($maxRetries * $retryDelay)s. Check logs with: az webapp log tail --resource-group $ResourceGroup --name $AppName"
}
finally {
    Pop-Location
}
