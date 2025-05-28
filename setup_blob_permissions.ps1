# Script to assign Azure Blob Storage permissions to a Managed Identity
# This script helps configure the necessary permissions for your application's Managed Identity
# to access Azure Blob Storage using Azure Role-Based Access Control (RBAC)

# Parameters
param(
    [Parameter(Mandatory=$true)]
    [string]$StorageAccountName,
    
    [Parameter(Mandatory=$true)]
    [string]$ResourceGroupName,
    
    [Parameter(Mandatory=$true)]
    [string]$PrincipalId,
    
    [Parameter(Mandatory=$false)]
    [string]$SubscriptionId = (Get-AzContext).Subscription.Id,
    
    [Parameter(Mandatory=$false)]
    [string]$Role = "Storage Blob Data Contributor"
)

# Ensure logged in to Azure
$context = Get-AzContext
if (-not $context) {
    Write-Host "You're not logged into Azure. Please run Connect-AzAccount first." -ForegroundColor Red
    exit
}

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  Assigning Blob Storage permissions to Managed Identity" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

# Set subscription context if provided
if ($SubscriptionId) {
    Set-AzContext -SubscriptionId $SubscriptionId | Out-Null
    Write-Host "Using subscription: $SubscriptionId" -ForegroundColor Green
}

# Get storage account resource
try {
    $storageAccount = Get-AzStorageAccount -ResourceGroupName $ResourceGroupName -Name $StorageAccountName -ErrorAction Stop
    Write-Host "Found storage account: $StorageAccountName" -ForegroundColor Green
}
catch {
    Write-Host "Error: Could not find storage account $StorageAccountName in resource group $ResourceGroupName" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit
}

# Get storage account resource ID
$resourceId = $storageAccount.Id
Write-Host "Storage Account Resource ID: $resourceId" -ForegroundColor Green

# Check if role assignment already exists
$existingAssignment = Get-AzRoleAssignment -ObjectId $PrincipalId -RoleDefinitionName $Role -Scope $resourceId -ErrorAction SilentlyContinue

if ($existingAssignment) {
    Write-Host "Role assignment already exists for this Managed Identity." -ForegroundColor Yellow
} else {
    # Assign role to the managed identity
    try {
        New-AzRoleAssignment -ObjectId $PrincipalId -RoleDefinitionName $Role -Scope $resourceId | Out-Null
        Write-Host "Successfully assigned '$Role' role to Managed Identity (Principal ID: $PrincipalId)" -ForegroundColor Green
    }
    catch {
        Write-Host "Error assigning role to Managed Identity:" -ForegroundColor Red
        Write-Host $_.Exception.Message -ForegroundColor Red
        exit
    }
}

# Verify role assignment
$verification = Get-AzRoleAssignment -ObjectId $PrincipalId -RoleDefinitionName $Role -Scope $resourceId

if ($verification) {
    Write-Host "Verified role assignment:" -ForegroundColor Green
    Write-Host "  - Role: $Role" -ForegroundColor Green
    Write-Host "  - Principal ID: $PrincipalId" -ForegroundColor Green
    Write-Host "  - Scope: $resourceId" -ForegroundColor Green
} else {
    Write-Host "WARNING: Could not verify role assignment. It may take some time for the assignment to propagate." -ForegroundColor Yellow
}

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "             Setup Complete" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "Usage instructions:" -ForegroundColor White
Write-Host "1. Your Managed Identity now has '$Role' permissions to the storage account." -ForegroundColor White
Write-Host "2. Your application can use DefaultAzureCredential to access blob storage." -ForegroundColor White
Write-Host "3. No connection strings or account keys are needed in your application." -ForegroundColor White
Write-Host "==================================================" -ForegroundColor Cyan
