# Managed Identity Authentication for Azure Services

The Data Catalog application has been updated to use Azure Managed Identity for authentication instead of using keys. The following changes were made:

## Changes in Authentication Method

### Previous Authentication Method
- Cosmos DB: Used account key for authentication
- Blob Storage: Used connection string with account key

### New Authentication Method
- Cosmos DB: Uses DefaultAzureCredential for authentication
- Blob Storage: Uses DefaultAzureCredential for authentication

## Benefits of Managed Identity

1. **Enhanced Security**: No keys or connection strings in code or configuration files
2. **Simplified Management**: No need to rotate keys regularly
3. **Reduced Risk**: Eliminates the possibility of key exposure
4. **Centralized Access Control**: Permissions managed through Azure RBAC

## Implementation Details

### Cosmos DB Client Initialization

```python
# Before
client = CosmosClient(ENDPOINT, credential=KEY)

# After
credential = DefaultAzureCredential()
client = CosmosClient(ENDPOINT, credential=credential)
```

### Blob Storage Client Initialization

```python
# Before
blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)

# After
credential = DefaultAzureCredential()
blob_service_client = BlobServiceClient(f"https://{AZURE_BLOB_ACCOUNT}.blob.core.windows.net", credential=credential)
```

### SAS Token Generation

```python
# Before
sas_token = generate_blob_sas(
    account_name=blob_service_client.account_name,
    container_name=AZURE_BLOB_CONTAINER,
    blob_name=blob_path,
    account_key=blob_service_client.credential.account_key,
    permission=BlobSasPermissions(read=True),
    expiry=datetime.utcnow() + timedelta(hours=hours_valid)
)

# After
user_delegation_key = blob_service_client.get_user_delegation_key(
    key_start_time=start_time,
    key_expiry_time=expiry_time
)

sas_token = generate_blob_sas(
    account_name=blob_service_client.account_name,
    container_name=AZURE_BLOB_CONTAINER,
    blob_name=blob_path,
    user_delegation_key=user_delegation_key,
    permission=BlobSasPermissions(read=True),
    expiry=expiry_time,
    start=start_time
)
```

## Configuration Changes

### Environment Variables

```
# Before
COSMOSDB_ENDPOINT=your_cosmosdb_endpoint
COSMOSDB_KEY=your_cosmosdb_key
COSMOSDB_DATABASE=datacatalog
COSMOSDB_CONTAINER=metadata
AZURE_STORAGE_CONNECTION_STRING=your_storage_connection_string
AZURE_BLOB_CONTAINER=datasets

# After
COSMOSDB_ENDPOINT=your_cosmosdb_endpoint
COSMOSDB_DATABASE=datacatalog
COSMOSDB_CONTAINER=metadata
AZURE_BLOB_ACCOUNT=your_storage_account_name
AZURE_BLOB_CONTAINER=datasets
```

## Required Azure Setup

### Azure RBAC Setup for Cosmos DB
```powershell
.\setup_cosmos_permissions.ps1 -CosmosAccountName "your-cosmos-account" -ResourceGroupName "your-resource-group" -PrincipalId "your-managed-identity-principal-id"
```

### Azure RBAC Setup for Blob Storage
```powershell
.\setup_blob_permissions.ps1 -StorageAccountName "yourstorageaccount" -ResourceGroupName "your-resource-group" -PrincipalId "your-managed-identity-principal-id"
```

## Testing the Configuration

1. Ensure your development environment is correctly set up with authentication to Azure:
   - When running locally, Azure CLI or Visual Studio authentication will be used
   - In Azure App Service, the managed identity of the service will be used

2. The application should connect to the Azure services without any keys or connection strings.

3. If you encounter permission issues, verify that the correct roles have been assigned to the identity:
   - For Cosmos DB: "DocumentDB Account Contributor" role
   - For Blob Storage: "Storage Blob Data Contributor" role
