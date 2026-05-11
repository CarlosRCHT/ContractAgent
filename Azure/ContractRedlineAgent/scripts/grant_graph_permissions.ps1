<#
.SYNOPSIS
  Grants Microsoft Graph application permissions to two Logic App
  system-assigned managed identities (download + upload workflows).

.DESCRIPTION
  Runs after deploy/bicep/main.bicep. Requires you to be signed in with an
  account that has the Privileged Role Administrator or Global Administrator
  role to consent to Graph application permissions.

  Default permissions are Sites.ReadWrite.All + Files.ReadWrite.All. For a
  least-privilege deployment, switch to Sites.Selected and grant per-site
  access via Microsoft Graph (out of scope for this script).

.PARAMETER ResourceGroupName
  Resource group containing the deployed Logic Apps.

.PARAMETER DownloadWorkflowName
  Name of the download Logic App (default: contract-redline-download).

.PARAMETER UploadWorkflowName
  Name of the upload Logic App (default: contract-redline-upload).

.PARAMETER GraphPermissions
  Application permissions to grant. Default: Sites.ReadWrite.All, Files.ReadWrite.All.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string] $ResourceGroupName,
    [string] $DownloadWorkflowName = 'contract-redline-download',
    [string] $UploadWorkflowName = 'contract-redline-upload',
    [string[]] $GraphPermissions = @('Sites.ReadWrite.All', 'Files.ReadWrite.All')
)

$ErrorActionPreference = 'Stop'

function Get-PrincipalId([string]$Name) {
    $id = az resource show `
        --resource-group $ResourceGroupName `
        --name $Name `
        --resource-type Microsoft.Logic/workflows `
        --query identity.principalId -o tsv
    if (-not $id) { throw "Could not resolve principalId for $Name" }
    return $id
}

function Grant-GraphPermission {
    param(
        [string]$PrincipalId,
        [string]$Permission,
        [string]$GraphSpId,
        [object[]]$AppRoles
    )
    $role = $AppRoles | Where-Object { $_.value -eq $Permission }
    if (-not $role) { throw "Graph app role not found: $Permission" }

    $body = @{
        principalId = $PrincipalId
        resourceId  = $GraphSpId
        appRoleId   = $role.id
    } | ConvertTo-Json -Compress

    # Write body to a temp file to avoid PowerShell JSON escaping issues with az rest
    $tmpFile = [System.IO.Path]::GetTempFileName()
    Set-Content -Path $tmpFile -Value $body -Encoding UTF8

    Write-Host "  granting $Permission to $PrincipalId..."
    az rest --method POST `
        --uri "https://graph.microsoft.com/v1.0/servicePrincipals/$PrincipalId/appRoleAssignments" `
        --headers 'Content-Type=application/json' `
        --body "@$tmpFile" | Out-Null

    Remove-Item $tmpFile -ErrorAction SilentlyContinue
}

Write-Host "Resolving Microsoft Graph service principal..."
$graphSp = az ad sp show --id 00000003-0000-0000-c000-000000000000 -o json | ConvertFrom-Json
$graphSpId = $graphSp.id
$appRoles = $graphSp.appRoles

foreach ($name in @($DownloadWorkflowName, $UploadWorkflowName)) {
    Write-Host "Granting permissions to '$name'..."
    $pid_ = Get-PrincipalId -Name $name
    foreach ($p in $GraphPermissions) {
        try {
            Grant-GraphPermission -PrincipalId $pid_ -Permission $p -GraphSpId $graphSpId -AppRoles $appRoles
        }
        catch {
            if ($_.Exception.Message -match 'Permission being assigned already exists') {
                Write-Host "  (already granted)"
            } else { throw }
        }
    }
}

Write-Host "Done."
