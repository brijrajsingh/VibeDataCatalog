import os
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
import pandas as pd
import io
import re
import uuid
from datetime import datetime, timedelta
import pytz
from .cosmos_client import metadata_container, activities_container

# Azure Blob Storage Configuration
AZURE_STORAGE_CONNECTION_STRING = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
AZURE_BLOB_CONTAINER = os.environ.get("AZURE_BLOB_CONTAINER")

# Initialize Blob Storage client
blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
blob_container_client = blob_service_client.get_container_client(AZURE_BLOB_CONTAINER)

def get_dataset_file_preview(blob_path):
    """
    Get a preview of a dataset file from Azure Blob storage
    For CSV and Excel files, returns the first 10 rows and header information
    For PDF files, returns text content from first few pages
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
    elif blob_path.lower().endswith('.pdf'):
        try:
            import pypdf
            from io import BytesIO
            
            pdf_reader = pypdf.PdfReader(BytesIO(file_content))
            num_pages = len(pdf_reader.pages)
            
            # Extract text from first few pages
            text_content = ""
            max_pages = min(3, num_pages)  # Preview first 3 pages
            for page_num in range(max_pages):
                page = pdf_reader.pages[page_num]
                text_content += f"--- Page {page_num + 1} ---\n"
                text_content += page.extract_text()
                text_content += "\n\n"
            
            return {
                'type': 'pdf',
                'preview': text_content[:2000],  # Limit to first 2000 characters
                'pdf_pages': num_pages,
                'text_content': text_content[:2000]
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
    items = list(metadata_container.query_items(query=query, enable_cross_partition_query=True))
    
    if not items:
        return {"nodes": [], "links": []}
    
    dataset = items[0]
    base_name = dataset.get('base_name', dataset['name'])
    
    # Get all versions of this dataset
    query = f"SELECT * FROM c WHERE c.base_name = '{base_name}'"
    all_versions = list(metadata_container.query_items(query=query, enable_cross_partition_query=True))
    
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
    # Generate SAS token for blob access
    sas_token = generate_blob_sas(
        account_name=blob_service_client.account_name,
        container_name=AZURE_BLOB_CONTAINER,
        blob_name=blob_path,
        account_key=blob_service_client.credential.account_key,
        permission=BlobSasPermissions(read=True),
        expiry=datetime.utcnow() + timedelta(hours=hours_valid)
    )
    
    # Create the full URL with SAS token
    blob_url = f"https://{blob_service_client.account_name}.blob.core.windows.net/{AZURE_BLOB_CONTAINER}/{blob_path}?{sas_token}"
    
    return blob_url

def validate_dataset_name(name):
    """
    Validate dataset name - only allow alphanumeric, spaces, hyphens, and underscores
    Returns (is_valid, error_message)
    """
    if not name or not name.strip():
        return False, "Dataset name cannot be empty"
    
    # Check length
    if len(name) < 3:
        return False, "Dataset name must be at least 3 characters long"
    
    if len(name) > 100:
        return False, "Dataset name cannot exceed 100 characters"
    
    # Only allow alphanumeric, spaces, hyphens, underscores, and periods
    # Also allow 'v' followed by numbers for versioning (e.g., "v1", "v2")
    pattern = r'^[a-zA-Z0-9\s\-_.]+$'
    if not re.match(pattern, name):
        return False, "Dataset name can only contain letters, numbers, spaces, hyphens, underscores, and periods"
    
    # Check that it doesn't start or end with special characters
    if name[0] in ['-', '_', '.', ' '] or name[-1] in ['-', '_', '.', ' ']:
        return False, "Dataset name cannot start or end with special characters or spaces"
    
    # Check for consecutive special characters
    if re.search(r'[\s\-_.]{2,}', name):
        return False, "Dataset name cannot contain consecutive special characters"
    
    return True, None

def sanitize_dataset_name(name):
    """
    Sanitize dataset name by removing or replacing invalid characters
    """
    if not name:
        return ""
    
    # Remove leading/trailing whitespace
    name = name.strip()
    
    # Replace multiple spaces with single space
    name = re.sub(r'\s+', ' ', name)
    
    # Remove any characters that aren't alphanumeric, space, hyphen, underscore, or period
    name = re.sub(r'[^a-zA-Z0-9\s\-_.]', '', name)
    
    # Remove leading/trailing special characters
    name = re.sub(r'^[\s\-_.]+|[\s\-_.]+$', '', name)
    
    # Replace consecutive special characters with single instance
    name = re.sub(r'([\s\-_.])\1+', r'\1', name)
    
    return name

def convert_to_local_time(datasets, timezone='Asia/Calcutta'):
    """Convert UTC timestamps to local timezone"""
    for dataset in datasets:
        if 'created_at' in dataset:
            utc_time = datetime.fromisoformat(dataset['created_at'])
            utcmoment = utc_time.replace(tzinfo=pytz.utc)
            localFormat = "%Y-%m-%d %H:%M:%S"
            local_time = utcmoment.astimezone(pytz.timezone(timezone))
            dataset['created_at_local'] = local_time.strftime(localFormat)
        
        # Convert file timestamps
        if 'files' in dataset:
            for file in dataset['files']:
                if 'uploaded_at' in file:
                    utc_time = datetime.fromisoformat(file['uploaded_at'])
                    utcmoment = utc_time.replace(tzinfo=pytz.utc)
                    local_time = utcmoment.astimezone(pytz.timezone(timezone))
                    file['uploaded_at_local'] = local_time.strftime(localFormat)

def group_datasets_by_base_name(datasets):
    """Group datasets by their base name"""
    grouped = {}
    for dataset in datasets:
        base_name = dataset.get('base_name', dataset['name'])
        if base_name not in grouped:
            grouped[base_name] = []
        grouped[base_name].append(dataset)
    
    # Sort versions within each group
    for base_name in grouped:
        grouped[base_name].sort(key=lambda x: x.get('version', 1), reverse=True)
    
    return grouped

def log_user_activity(username, activity_type, message, dataset_id=None, file_id=None):
    """Log user activity to the activities container"""
    try:
        activity = {
            'id': str(uuid.uuid4()),
            'username': username,
            'timestamp': datetime.utcnow().isoformat(),
            'activity_type': activity_type,
            'message': message
        }
        
        if dataset_id:
            activity['dataset_id'] = dataset_id
        if file_id:
            activity['file_id'] = file_id
        
        activities_container.create_item(body=activity)
    except Exception:
        # Don't fail if activity tracking fails
        pass
