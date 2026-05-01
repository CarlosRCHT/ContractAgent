@description('Location for all resources')
param location string = 'canadacentral'

@description('Name prefix for resources')
param namePrefix string = 'contract-redline'

@description('SKU for the App Service Plan')
param appServiceSku string = 'B1'

// App Service Plan
resource appServicePlan 'Microsoft.Web/serverfarms@2023-01-01' = {
  name: '${namePrefix}-plan'
  location: location
  kind: 'linux'
  sku: {
    name: appServiceSku
  }
  properties: {
    reserved: true  // Required for Linux
  }
}

// App Service
resource webApp 'Microsoft.Web/sites@2023-01-01' = {
  name: '${namePrefix}-app'
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: appServicePlan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'PYTHON|3.11'
      appCommandLine: 'startup.sh'
      alwaysOn: true
      minTlsVersion: '1.2'
      ftpsState: 'Disabled'
      appSettings: [
        {
          name: 'SCM_DO_BUILD_DURING_DEPLOYMENT'
          value: 'true'
        }
        {
          name: 'WEBSITES_PORT'
          value: '8000'
        }
      ]
    }
  }
}

output appServiceName string = webApp.name
output appServiceUrl string = 'https://${webApp.properties.defaultHostName}'
output managedIdentityPrincipalId string = webApp.identity.principalId
