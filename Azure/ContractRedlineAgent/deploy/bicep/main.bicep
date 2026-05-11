// Deploys two Consumption Logic Apps (download + upload) with system-assigned
// managed identity, intended to back the Foundry agent's Microsoft Graph
// access. The MIs require Microsoft Graph application permissions (Sites.Selected
// or Sites.ReadWrite.All + Files.ReadWrite.All); grant them with the helper at
// scripts/grant_graph_permissions.ps1 after deployment.

@description('Prefix for Logic App names.')
param namePrefix string = 'contract-redline'

@description('Azure region.')
param location string = resourceGroup().location

@description('Tags to apply to all resources.')
param tags object = {
  workload: 'contract-redline-agent'
}

var downloadWorkflowName = '${namePrefix}-download'
var uploadWorkflowName = '${namePrefix}-upload'

resource downloadWorkflow 'Microsoft.Logic/workflows@2019-05-01' = {
  name: downloadWorkflowName
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    state: 'Enabled'
    definition: loadJsonContent('../logicapps/download_workflow.json')
    parameters: {}
  }
}

resource uploadWorkflow 'Microsoft.Logic/workflows@2019-05-01' = {
  name: uploadWorkflowName
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    state: 'Enabled'
    definition: loadJsonContent('../logicapps/upload_workflow.json')
    parameters: {}
  }
}

output downloadWorkflowName string = downloadWorkflow.name
output uploadWorkflowName string = uploadWorkflow.name
output downloadPrincipalId string = downloadWorkflow.identity.principalId
output uploadPrincipalId string = uploadWorkflow.identity.principalId

#disable-next-line outputs-should-not-contain-secrets
output downloadCallbackHint string = 'Run: az rest --method post --uri ${environment().resourceManager}subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Logic/workflows/${downloadWorkflowName}/triggers/manual/listCallbackUrl?api-version=2016-06-01'
#disable-next-line outputs-should-not-contain-secrets
output uploadCallbackHint string = 'Run: az rest --method post --uri ${environment().resourceManager}subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Logic/workflows/${uploadWorkflowName}/triggers/manual/listCallbackUrl?api-version=2016-06-01'
