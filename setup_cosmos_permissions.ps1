# Script to assign Cosmos DB permissions to a Managed Identity
# This script helps configure the necessary permissions for your application's Managed Identity
# to access Cosmos DB using Azure Role-Based Access Control (RBAC)

# Parameters
param(
    [Parameter(Mandatory=$true)]
    [string]$CosmosAccountName,
    
    [Parameter(Mandatory=$true)]
    [string]$ResourceGroupName,
    
    [Parameter(Mandatory=$true)]
    [string]$PrincipalId,
    
    [Parameter(Mandatory=$false)]
    [string]$SubscriptionId = (Get-AzContext).Subscription.Id,
    
    [Parameter(Mandatory=$false)]
    [string]$Role = "DocumentDB Account Contributor"
)

# Ensure logged in to Azure
$context = Get-AzContext
if (-not $context) {
    Write-Host "You're not logged into Azure. Please run Connect-AzAccount first." -ForegroundColor Red
    exit
}

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  Assigning Cosmos DB permissions to Managed Identity" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

# Verify subscription
Write-Host "Using subscription: $($context.Subscription.Name) ($SubscriptionId)" -ForegroundColor Yellow
Write-Host ""

# Get the resource ID for the Cosmos DB account
try {
    Write-Host "Getting Cosmos DB account resource ID..." -ForegroundColor Green
    $cosmosDbAccount = Get-AzCosmosDBAccount -ResourceGroupName $ResourceGroupName -Name $CosmosAccountName
    $cosmosDbResourceId = $cosmosDbAccount.Id
    
    if (-not $cosmosDbResourceId) {
        Write-Host "Could not find Cosmos DB account $CosmosAccountName in resource group $ResourceGroupName." -ForegroundColor Red
        exit
    }
    
    Write-Host "Found Cosmos DB: $CosmosAccountName" -ForegroundColor Green
    Write-Host "Resource ID: $cosmosDbResourceId" -ForegroundColor Green
    Write-Host ""
} 
catch {
    Write-Host "Error finding Cosmos DB account: $_" -ForegroundColor Red
    exit
}

# Assign role to Managed Identity
try {
    Write-Host "Assigning '$Role' role to Principal ID $PrincipalId..." -ForegroundColor Green
    
    # Check if role assignment already exists
    $existingAssignment = Get-AzRoleAssignment -ObjectId $PrincipalId -RoleDefinitionName $Role -Scope $cosmosDbResourceId -ErrorAction SilentlyContinue
    
    if ($existingAssignment) {
        Write-Host "Role assignment already exists." -ForegroundColor Yellow
    } else {
        $roleAssignment = New-AzRoleAssignment -ObjectId $PrincipalId -RoleDefinitionName $Role -Scope $cosmosDbResourceId
        Write-Host "Role successfully assigned!" -ForegroundColor Green
    }
    
    Write-Host ""
    Write-Host "Principal ID $PrincipalId now has '$Role' access to Cosmos DB account $CosmosAccountName" -ForegroundColor Green
}
catch {
    Write-Host "Error assigning role: $_" -ForegroundColor Red
    exit
}

Write-Host ""
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  Managed Identity permission setup complete!" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "To use this script:" -ForegroundColor White
Write-Host "1. First get your Managed Identity's Principal ID:" -ForegroundColor White
Write-Host "   - For App Service: az webapp identity show --name <app-name> --resource-group <resource-group>" -ForegroundColor White
Write-Host "   - For VM: az vm identity show --name <vm-name> --resource-group <resource-group>" -ForegroundColor White
Write-Host ""
Write-Host "2. Then run this script with those values:" -ForegroundColor White
Write-Host "   .\setup_cosmos_permissions.ps1 -CosmosAccountName 'your-cosmos-account' -ResourceGroupName 'your-resource-group' -PrincipalId 'your-principal-id'" -ForegroundColor White
