import os
from azure.cosmos import CosmosClient
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
import pandas as pd
import io

# Azure Configuration
ENDPOINT = os.environ.get("COSMOSDB_ENDPOINT")
DATABASE_NAME = os.environ.get("COSMOSDB_DATABASE")
CONTAINER_NAME = os.environ.get("COSMOSDB_CONTAINER")
AZURE_BLOB_ACCOUNT = os.environ.get("AZURE_BLOB_ACCOUNT")
AZURE_BLOB_CONTAINER = os.environ.get("AZURE_BLOB_CONTAINER")

# Initialize Azure credential
credential = DefaultAzureCredential()

# Initialize CosmosDB client
client = CosmosClient(ENDPOINT, credential=credential)
database = client.get_database_client(DATABASE_NAME)
container = database.get_container_client(CONTAINER_NAME)

# Initialize Blob Storage client with DefaultAzureCredential
blob_service_client = BlobServiceClient(f"https://{AZURE_BLOB_ACCOUNT}.blob.core.windows.net", credential=credential)
blob_container_client = blob_service_client.get_container_client(AZURE_BLOB_CONTAINER)

def get_dataset_file_preview(blob_path):
    """
    Get a preview of a dataset file from Azure Blob storage
    For CSV and Excel files, returns the first 10 rows and header information
    For other text-based files, returns the first 10 lines
    """
    blob_client = blob_service_client.get_blob_client(container=AZURE_BLOB_CONTAINER, blob=blob_path)
    
    # Download the blob content
    file_content = blob_client.download_blob().readall()
    
    # Handle different file types
    if blob_path.lower().endswith('.csv'):
        try:
            df = pd.read_csv(io.BytesIO(file_content))
            # Get column information
            column_info = {
                'count': len(df.columns),
                'names': list(df.columns)
            }
            # Generate HTML preview with first 10 rows
            preview_html = df.head(10).to_html(classes="table table-striped table-sm", index=False)
            return {
                'type': 'csv',
                'column_info': column_info,
                'preview': preview_html,
                'row_count': len(df)
            }
        except Exception as e:
            return {
                'type': 'error', 
                'error': str(e)
            }
    elif blob_path.lower().endswith(('.xlsx', '.xls')):
        try:
            # Explicitly use openpyxl engine for Excel files
            df = pd.read_excel(io.BytesIO(file_content), engine='openpyxl')
            # Get column information
            column_info = {
                'count': len(df.columns),
                'names': list(df.columns)
            }
            # Generate HTML preview with first 10 rows
            preview_html = df.head(10).to_html(classes="table table-striped table-sm", index=False)
            return {
                'type': 'excel',
                'column_info': column_info,
                'preview': preview_html,
                'row_count': len(df)
            }
        except Exception as e:
            return {
                'type': 'error', 
                'error': str(e)
            }
            
    # Handle text files
    elif blob_path.lower().endswith(('.txt', '.json', '.md', '.py', '.js', '.html', '.css')):
        try:
            text_content = file_content.decode('utf-8', errors='replace')
            lines = text_content.split('\n')
            preview_lines = lines[:10]
            return {
                'type': 'text',
                'preview': '\n'.join(preview_lines),
                'line_count': len(lines)
            }
        except Exception as e:
            return {
                'type': 'error', 
                'error': str(e)
            }
            
    else:
        return {
            'type': 'unsupported',
            'message': "Preview not available for this file type"
        }

def get_dataset_lineage_tree(dataset_id):
    """
    Get the complete lineage tree for a dataset
    Returns a dictionary with nodes and links for visualization
    """
    # Get the initial dataset
    query = f"SELECT * FROM c WHERE c.id = '{dataset_id}'"
    items = list(container.query_items(query=query, enable_cross_partition_query=True))
    
    if not items:
        return {"nodes": [], "links": []}
    
    dataset = items[0]
    base_name = dataset.get('base_name', dataset['name'])
    
    # Get all versions of this dataset
    query = f"SELECT * FROM c WHERE c.base_name = '{base_name}'"
    all_versions = list(container.query_items(query=query, enable_cross_partition_query=True))
    
    # Build nodes and links
    nodes = []
    links = []
    
    for version in all_versions:
        nodes.append({
            "id": version["id"],
            "name": version["name"],
            "version": version["version"],
            "tags": version.get("tags", [])
        })
        
        if version.get("parent_id"):
            links.append({
                "source": version["parent_id"],
                "target": version["id"],
                "type": "version"
            })
    
    return {"nodes": nodes, "links": links}

def generate_blob_sas_url(blob_path, hours_valid=1):
    """
    Generate a URL with SAS token for direct access to a blob in Azure Storage
    
    Args:
        blob_path: Path to the blob in the container
        hours_valid: Number of hours the SAS token should be valid for
        
    Returns:
        Full URL with SAS token
    """
    from datetime import datetime, timedelta
    from azure.storage.blob import generate_blob_sas, BlobSasPermissions
    
    # Get a blob client for the specific blob
    blob_client = blob_container_client.get_blob_client(blob_path)
    
    # Generate a user delegation key that will be used to create the SAS
    start_time = datetime.utcnow()
    expiry_time = start_time + timedelta(hours=hours_valid)
    
    # Generate the SAS token using DefaultAzureCredential
    user_delegation_key = blob_service_client.get_user_delegation_key(
        key_start_time=start_time,
        key_expiry_time=expiry_time
    )
    
    # Generate SAS token using the user delegation key
    sas_token = generate_blob_sas(
        account_name=blob_service_client.account_name,
        container_name=AZURE_BLOB_CONTAINER,
        blob_name=blob_path,
        user_delegation_key=user_delegation_key,
        permission=BlobSasPermissions(read=True),
        expiry=expiry_time,
        start=start_time
    )
    
    # Create the full URL with SAS token
    blob_url = f"https://{blob_service_client.account_name}.blob.core.windows.net/{AZURE_BLOB_CONTAINER}/{blob_path}?{sas_token}"
    
    return blob_url
