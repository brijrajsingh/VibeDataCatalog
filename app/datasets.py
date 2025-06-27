from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from azure.cosmos import CosmosClient
from azure.storage.blob import BlobServiceClient, BlobClient, generate_blob_sas, BlobSasPermissions
from datetime import datetime, timedelta
import uuid
import os
import pandas as pd
import io
from pytz import timezone  # Import timezone for local time conversion
import pytz

# Azure Configuration
ENDPOINT = os.environ.get("COSMOSDB_ENDPOINT")
KEY = os.environ.get("COSMOSDB_KEY")
DATABASE_NAME = os.environ.get("COSMOSDB_DATABASE")
CONTAINER_NAME = os.environ.get("COSMOSDB_CONTAINER")
AZURE_STORAGE_CONNECTION_STRING = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
AZURE_BLOB_CONTAINER = os.environ.get("AZURE_BLOB_CONTAINER")

# Initialize CosmosDB client
client = CosmosClient(ENDPOINT, credential=KEY)
database = client.get_database_client(DATABASE_NAME)
container = database.get_container_client(CONTAINER_NAME)

# Initialize Blob Storage client
blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
blob_container_client = blob_service_client.get_container_client(AZURE_BLOB_CONTAINER)

# Blueprint for dataset routes
datasets_bp = Blueprint('datasets', __name__, url_prefix='/datasets')

@datasets_bp.route('/')
@login_required
def list_datasets():
    """List all datasets"""
    show_deleted = request.args.get('show_deleted', '').lower() == 'true'
    browser_timezone = request.args.get('timezone', 'Asia/Calcutta')  # Default to Asia/Calcutta timezone
    
    # Exclude deleted datasets unless specifically requested
    if show_deleted:
        query = "SELECT * FROM c WHERE c.type = 'dataset' ORDER BY c._ts DESC"
    else:
        query = "SELECT * FROM c WHERE c.type = 'dataset' AND NOT IS_DEFINED(c.is_deleted) ORDER BY c._ts DESC"
        
    datasets = list(container.query_items(query=query, enable_cross_partition_query=True))
    
    # Convert created_at to local time for each dataset
    for dataset in datasets:
        if 'created_at' in dataset:
            utc_time = datetime.fromisoformat(dataset['created_at'])
            utcmoment = utc_time.replace(tzinfo=pytz.utc)
            localFormat = "%Y-%m-%d %H:%M:%S"            
            local_time = utcmoment.astimezone(pytz.timezone(browser_timezone))
            dataset['created_at_local'] = local_time.strftime(localFormat)
            dataset['created_at'] = dataset['created_at_local']  # Update created_at with local time
    
    # Group datasets by their base name to show versions
    dataset_groups = {}
    for dataset in datasets:
        base_name = dataset.get('base_name', dataset['name'])
        if base_name not in dataset_groups:
            dataset_groups[base_name] = []
        dataset_groups[base_name].append(dataset)
    
    return render_template('datasets/list.html', dataset_groups=dataset_groups, show_deleted=show_deleted)

@datasets_bp.route('/register', methods=['GET', 'POST'])
@login_required
def register_dataset():
    """Register a new dataset"""
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        tags = [tag.strip() for tag in request.form.get('tags', '').split(',') if tag.strip()]
        
        # Check if a dataset with the same name already exists
        query = f"SELECT * FROM c WHERE c.type = 'dataset' AND c.name = '{name}'"
        existing_datasets = list(container.query_items(query=query, enable_cross_partition_query=True))
        
        if existing_datasets:
            flash(f"A dataset with the name '{name}' already exists. Please choose a different name.", 'error')
            return redirect(request.url)
        
        # Create a new dataset record
        dataset_id = str(uuid.uuid4())
        dataset = {
            'id': dataset_id,
            'type': 'dataset',
            'name': name,
            'base_name': name,  # Store original name for versioning
            'description': description,
            'tags': tags,
            'version': 1,
            'created_by': current_user.username,
            'created_at': datetime.utcnow().isoformat(),
            'files': [],
            'parent_id': None  # No parent for first version
        }
        
        container.create_item(body=dataset)
        flash('Dataset registered successfully', 'success')
        return redirect(url_for('datasets.view_dataset', dataset_id=dataset_id))
    
    return render_template('datasets/register.html')

@datasets_bp.route('/<dataset_id>')
@login_required
def view_dataset(dataset_id):
     # Convert uploaded_at to local time for each file
    browser_timezone = request.args.get('timezone', 'UTC')  # Default to UTC if not provided

    """View a specific dataset"""
    query = f"SELECT * FROM c WHERE c.id = '{dataset_id}'"
    items = list(container.query_items(query=query, enable_cross_partition_query=True))
    
    if not items:
        flash('Dataset not found', 'error')
        return redirect(url_for('datasets.list_datasets'))
    
    dataset = items[0]
    utc_time = datetime.fromisoformat(dataset['created_at'])
    utcmoment = utc_time.replace(tzinfo=pytz.utc)
    localFormat = "%Y-%m-%d %H:%M:%S"            
    local_time = utcmoment.astimezone(pytz.timezone(browser_timezone))
    dataset['created_at_local'] = local_time.strftime(localFormat)
    dataset['created_at'] = dataset['created_at_local']  # Update created_at with local time  
    
   
    for file in dataset.get('files', []):
        if 'uploaded_at' in file:
            utc_time = datetime.fromisoformat(file['uploaded_at'])
            utcmoment = utc_time.replace(tzinfo=pytz.utc)
            localFormat = "%Y-%m-%d %H:%M:%S"            
            local_time = utcmoment.astimezone(pytz.timezone(browser_timezone))
            file['uploaded_at_local'] = local_time.strftime(localFormat)
            file['uploaded_at'] = file['uploaded_at_local']  # Update created_at with local time  
    
    # Get dataset versions (including deleted ones for admin view)
    query = f"SELECT * FROM c WHERE c.base_name = '{dataset['base_name']}' ORDER BY c.version DESC"
    versions = list(container.query_items(query=query, enable_cross_partition_query=True))
    
    # Get lineage information
    lineage = []
    current = dataset
    while current.get('parent_id'):
        query = f"SELECT * FROM c WHERE c.id = '{current['parent_id']}'"
        parent_items = list(container.query_items(query=query, enable_cross_partition_query=True))
        if parent_items:
            parent = parent_items[0]
            lineage.append(parent)
            current = parent
        else:
            break
    
    return render_template('datasets/view.html', dataset=dataset, versions=versions, lineage=lineage)

@datasets_bp.route('/<dataset_id>/upload', methods=['GET', 'POST'])
@login_required
def upload_file(dataset_id):
    """Upload a file to a dataset"""
    query = f"SELECT * FROM c WHERE c.id = '{dataset_id}'"
    items = list(container.query_items(query=query, enable_cross_partition_query=True))
    
    if not items:
        flash('Dataset not found', 'error')
        return redirect(url_for('datasets.list_datasets'))
    
    dataset = items[0]
    
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        
        if file.filename == '':
            flash('No selected file', 'error')
            return redirect(request.url)
        
        if file:
            # Validate file type
            filename = file.filename.lower()
            allowed_extensions = ['.csv', '.xlsx', '.xls', '.pdf']
            
            if not any(filename.endswith(ext) for ext in allowed_extensions):
                flash('Invalid file type. Only CSV, Excel (.xlsx, .xls), and PDF files are allowed.', 'error')
                return redirect(request.url)
            
            # Save file to Azure Blob Storage
            filename = file.filename
            file_id = str(uuid.uuid4())
            blob_path = f"{dataset['base_name']}/{dataset['version']}/{file_id}_{filename}"
            
            # Upload to blob storage
            blob_client = blob_service_client.get_blob_client(container=AZURE_BLOB_CONTAINER, blob=blob_path)
            blob_client.upload_blob(file)
            
            # Reset file pointer and calculate file size in kilobytes
            file.seek(0, io.SEEK_END)  # Move to the end of the file to get its size
            size_bytes = file.tell()
            file.seek(0)  # Reset pointer for further operations
            size_kb = size_bytes / 1024            
           
            # Update dataset metadata
            file_info = {
                'id': file_id,
                'filename': filename,
                'blob_path': blob_path,
                'uploaded_by': current_user.username,
                'uploaded_at': datetime.utcnow().isoformat(),
                'size_bytes': size_bytes,
                'size_kb': round(size_kb, 2)  # Store size in KB rounded to 2 decimal places
            }
            
            dataset['files'].append(file_info)
            container.upsert_item(dataset)
            
            flash('File uploaded successfully', 'success')
            return redirect(url_for('datasets.view_dataset', dataset_id=dataset_id))
    
    return render_template('datasets/upload.html', dataset=dataset)

@datasets_bp.route('/<dataset_id>/new_version', methods=['GET', 'POST'])
@login_required
def new_version(dataset_id):
    """Create a new version of a dataset"""
    query = f"SELECT * FROM c WHERE c.id = '{dataset_id}'"
    items = list(container.query_items(query=query, enable_cross_partition_query=True))
    
    if not items:
        flash('Dataset not found', 'error')
        return redirect(url_for('datasets.list_datasets'))
    
    parent_dataset = items[0]
    if request.method == 'POST':
        # Get all versions to find the maximum version number
        query = f"SELECT c.version FROM c WHERE c.type = 'dataset' AND c.base_name = '{parent_dataset['base_name']}'"
        version_items = list(container.query_items(query=query, enable_cross_partition_query=True))
        
        # Manually find the maximum version
        versions = [item['version'] for item in version_items if 'version' in item]
        max_version = max(versions) if versions else parent_dataset['version']
        new_version = max_version + 1
        
        # Create new version with inherited properties
        new_dataset_id = str(uuid.uuid4())
        new_dataset = {
            'id': new_dataset_id,
            'type': 'dataset',
            'name': f"{parent_dataset['base_name']} v{new_version}",
            'base_name': parent_dataset['base_name'],
            'description': request.form.get('description', parent_dataset['description']),
            'tags': [tag.strip() for tag in request.form.get('tags', ','.join(parent_dataset['tags'])).split(',') if tag.strip()],
            'version': new_version,
            'created_by': current_user.username,
            'created_at': datetime.utcnow().isoformat(),
            'files': [],
            'parent_id': parent_dataset['id']  # Link to parent
        }
        
        container.create_item(body=new_dataset)
        flash('New dataset version created', 'success')
        return redirect(url_for('datasets.view_dataset', dataset_id=new_dataset_id))
    
    return render_template('datasets/new_version.html', dataset=parent_dataset)

@datasets_bp.route('/<dataset_id>/file/<file_id>')
@login_required
def get_file(dataset_id, file_id):
    """Get a file from a dataset with a SAS URL for access"""
    query = f"SELECT * FROM c WHERE c.id = '{dataset_id}'"
    items = list(container.query_items(query=query, enable_cross_partition_query=True))
    
    if not items:
        flash('Dataset not found', 'error')
        return redirect(url_for('datasets.list_datasets'))
    
    dataset = items[0]
    
    # Find the file
    file_info = None
    for file in dataset['files']:
        if file['id'] == file_id:
            file_info = file
            break
    
    if not file_info:
        flash('File not found', 'error')
        return redirect(url_for('datasets.view_dataset', dataset_id=dataset_id))
      # Use the utility function to generate the blob URL with a 1-hour SAS token
    from .utils import generate_blob_sas_url
    blob_url = generate_blob_sas_url(file_info['blob_path'], hours_valid=1)
    
    # Track this download activity
    try:
        activity = {
            'id': str(uuid.uuid4()),
            'type': 'activity',
            'username': current_user.username,
            'timestamp': datetime.utcnow().isoformat(),
            'activity_type': 'file_download',
            'message': f"Downloaded file '{file_info['filename']}' from dataset '{dataset['name']}'",
            'dataset_id': dataset_id,
            'file_id': file_id
        }
        container.create_item(body=activity)
    except Exception:
        # Don't fail if activity tracking fails
        pass
    
    return redirect(blob_url)

@datasets_bp.route('/search')
@login_required
def search_datasets():
    """Search for datasets based on name, tags, or uploaded by"""
    query_term = request.args.get('query', '')
    show_deleted = request.args.get('show_deleted', '').lower() == 'true'
    
    if not query_term:
        return render_template('datasets/search.html', datasets=[], query='', show_deleted=show_deleted)
    
    # Parse the query for advanced search
    search_parts = query_term.split()
    tag_filters = []
    uploader_filters = []
    name_filters = []
    status_filter = None  # 'active', 'deleted', or None
    
    for part in search_parts:
        if part.startswith('tag:'):
            tag_filters.append(part[4:].lower())  # Store lowercase version of tag
        elif part.startswith('by:'):
            uploader_filters.append(part[3:].lower())  # Store lowercase version of uploader
        elif part == 'status:deleted':
            status_filter = 'deleted'
        elif part == 'status:active':
            status_filter = 'active'
        else:
            name_filters.append(part)
      # Construct the CosmosDB query
    filters = []
    
    # Handle deleted status
    if status_filter == 'deleted':
        filters.append("IS_DEFINED(c.is_deleted)")
    elif status_filter == 'active':
        filters.append("NOT IS_DEFINED(c.is_deleted)")
    elif not show_deleted:  # Default behavior is to hide deleted unless explicitly requested
        filters.append("NOT IS_DEFINED(c.is_deleted)")
    
    if name_filters:
        name_query = ' OR '.join([f"CONTAINS(LOWER(c.name), '{name.lower()}')" for name in name_filters])
        desc_query = ' OR '.join([f"CONTAINS(LOWER(c.description), '{name.lower()}')" for name in name_filters])
        filters.append(f"({name_query} OR {desc_query})")
    
    if uploader_filters:
        uploader_conditions = []
        for uploader in uploader_filters:
            uploader_conditions.append(f"LOWER(c.created_by) = '{uploader.lower()}'")
        filters.append(f"({' OR '.join(uploader_conditions)})")
    
    # For tag filters, we'll fetch datasets with tags and filter in Python
    has_tag_filter = bool(tag_filters)
    if has_tag_filter:
        # Just check that tags array exists and is not empty
        filters.append("(ARRAY_LENGTH(c.tags) > 0)")
    
    # Combine filters
    main_query = "SELECT * FROM c WHERE c.type = 'dataset'"
    if filters:
        main_query += " AND " + " AND ".join(filters)
    
    # Execute query
    try:
        all_datasets = list(container.query_items(query=main_query, enable_cross_partition_query=True))
    except Exception as e:
        flash(f"Search error: {str(e)}", "error")
        return render_template('datasets/search.html', datasets=[], query=query_term)
    
    # Post-query filtering for tags (case-insensitive)
    if has_tag_filter:
        filtered_datasets = []
        for dataset in all_datasets:
            dataset_tags = []
            # Handle case where tags might be missing
            if 'tags' in dataset and dataset['tags']:
                dataset_tags = [tag.lower() for tag in dataset['tags']]
            
            # Check if all requested tags are present in this dataset's tags
            if all(tag_filter in dataset_tags for tag_filter in tag_filters):
                filtered_datasets.append(dataset)
                
        datasets = filtered_datasets
    else:
        datasets = all_datasets
    
    #set the created_at_local field for each dataset
    for dataset in datasets:
        if 'created_at' in dataset:
            utc_time = datetime.fromisoformat(dataset['created_at'])
            utcmoment = utc_time.replace(tzinfo=pytz.utc)
            localFormat = "%Y-%m-%d %H:%M:%S"            
            local_time = utcmoment.astimezone(pytz.timezone('Asia/Calcutta'))
            dataset['created_at_local'] = local_time.strftime(localFormat)
            dataset['created_at'] = dataset['created_at_local']
    
    return render_template('datasets/search.html', datasets=datasets, query=query_term, show_deleted=show_deleted)

@datasets_bp.route('/lineage')
@login_required
def lineage_view():
    """View the lineage graph of all datasets"""
    show_deleted = request.args.get('show_deleted', '').lower() == 'true'
    
    # Include deleted datasets if requested
    if show_deleted:
        query = "SELECT c.id, c.name, c.version, c.base_name, c.parent_id, c.tags, c.is_deleted FROM c WHERE c.type = 'dataset'"
    else:
        query = "SELECT c.id, c.name, c.version, c.base_name, c.parent_id, c.tags FROM c WHERE c.type = 'dataset' AND NOT IS_DEFINED(c.is_deleted)"
        
    datasets = list(container.query_items(query=query, enable_cross_partition_query=True))
    
    # Format data for the visualization
    nodes = []
    links = []
    
    # Create nodes for each dataset
    for dataset in datasets:
        node_data = {
            'id': dataset['id'],
            'name': dataset['name'],
            'version': dataset['version'],
            'base_name': dataset['base_name'],
            'tags': dataset.get('tags', [])
        }
        
        # Add deletion status for visualization styling
        if dataset.get('is_deleted'):
            node_data['is_deleted'] = True
            
        nodes.append(node_data)
        
        # Create links between versions
        if dataset.get('parent_id'):
            links.append({
                'source': dataset['parent_id'],
                'target': dataset['id']
            })
    
    return render_template('datasets/lineage.html', nodes=nodes, links=links, show_deleted=show_deleted)

@datasets_bp.route('/<dataset_id>/file/<file_id>/preview')
@login_required
def preview_file(dataset_id, file_id):
    """Preview the contents of a file from a dataset"""
     # Convert uploaded_at to local time for each file
    browser_timezone = request.args.get('timezone', 'UTC')  # Default to UTC if not provided

    # Get dataset information
    query = f"SELECT * FROM c WHERE c.id = '{dataset_id}'"
    items = list(container.query_items(query=query, enable_cross_partition_query=True))
    
    if not items:
        flash('Dataset not found', 'error')
        return redirect(url_for('datasets.list_datasets'))
    
    dataset = items[0]
    
    # Find the file
    file_info = None
    for file in dataset['files']:
        if file['id'] == file_id:
            file_info = file
            break
    
    if not file_info:
        flash('File not found', 'error')
        return redirect(url_for('datasets.view_dataset', dataset_id=dataset_id))
    
    # Convert uploaded_at to local time for the file
    browser_timezone = request.args.get('timezone', 'UTC')  # Default to UTC if not provided
    if 'uploaded_at' in file_info:
        utc_time = datetime.fromisoformat(file_info['uploaded_at'])
        utcmoment = utc_time.replace(tzinfo=pytz.utc)
        localFormat = "%Y-%m-%d %H:%M:%S"            
        local_time = utcmoment.astimezone(pytz.timezone(browser_timezone))
        file_info['uploaded_at_local'] = local_time.strftime(localFormat)
        file_info['uploaded_at'] = file_info['uploaded_at_local']  # Update created_at with local time           
    # Get file preview from utils
    from .utils import get_dataset_file_preview
    preview_data = get_dataset_file_preview(file_info['blob_path'])
    
    # Add file metadata to preview data
    preview_data['file_info'] = {
        'filename': file_info['filename'],
        'uploaded_by': file_info['uploaded_by'],
        'uploaded_at': file_info['uploaded_at_local'],  # Use local time
        'size_bytes': file_info['size_bytes']
    }
    
    return render_template('datasets/preview.html', 
                           dataset=dataset, 
                           file=file_info, 
                           preview_data=preview_data)

@datasets_bp.route('/<dataset_id>/file/<file_id>/direct-link')
@login_required
def get_file_direct_link(dataset_id, file_id):
    """Get a direct link to a file with a 5-hour SAS token"""
    query = f"SELECT * FROM c WHERE c.id = '{dataset_id}'"
    items = list(container.query_items(query=query, enable_cross_partition_query=True))
    
    if not items:
        flash('Dataset not found', 'error')
        return redirect(url_for('datasets.list_datasets'))
    
    dataset = items[0]
    
    # Find the file
    file_info = None
    for file in dataset['files']:
        if file['id'] == file_id:
            file_info = file
            break
    
    if not file_info:
        flash('File not found', 'error')
        return redirect(url_for('datasets.view_dataset', dataset_id=dataset_id))
    
    # Generate SAS URL for 5 hours
    from .utils import generate_blob_sas_url
    blob_url = generate_blob_sas_url(file_info['blob_path'], hours_valid=5)
    
    # Track this activity
    try:
        activity = {
            'id': str(uuid.uuid4()),
            'type': 'activity',
            'username': current_user.username,
            'timestamp': datetime.utcnow().isoformat(),
            'activity_type': 'file_view',
            'message': f"Viewed file '{file_info['filename']}' from dataset '{dataset['name']}'",
            'dataset_id': dataset_id,
            'file_id': file_id
        }
        container.create_item(body=activity)
    except Exception:
        # Don't fail if activity tracking fails
        pass
    
    return redirect(blob_url)

@datasets_bp.route('/<dataset_id>/delete', methods=['POST'])
@login_required
def soft_delete_dataset(dataset_id):
    """Soft delete a dataset version"""
    query = f"SELECT * FROM c WHERE c.id = '{dataset_id}'"
    items = list(container.query_items(query=query, enable_cross_partition_query=True))
    
    if not items:
        flash('Dataset not found', 'error')
        return redirect(url_for('datasets.list_datasets'))
    
    dataset = items[0]
    
    # Check if this is the only version of a dataset
    query = f"SELECT c.id FROM c WHERE c.type = 'dataset' AND c.base_name = '{dataset['base_name']}' AND NOT IS_DEFINED(c.is_deleted)"
    versions = list(container.query_items(query=query, enable_cross_partition_query=True))
    
    # Soft delete by adding is_deleted field
    dataset['is_deleted'] = True
    dataset['deleted_by'] = current_user.username
    dataset['deleted_at'] = datetime.utcnow().isoformat()
    
    container.upsert_item(dataset)
    
    # Track this activity
    try:
        activity = {
            'id': str(uuid.uuid4()),
            'type': 'activity',
            'username': current_user.username,
            'timestamp': datetime.utcnow().isoformat(),
            'activity_type': 'dataset_delete',
            'message': f"Soft deleted dataset '{dataset['name']}' (version {dataset['version']})",
            'dataset_id': dataset_id
        }
        container.create_item(body=activity)
    except Exception:
        # Don't fail if activity tracking fails
        pass
    
    flash(f"Dataset '{dataset['name']}' version {dataset['version']} has been deleted", 'success')
    
    # If we deleted the version we were viewing, redirect to the latest available version
    # or to the datasets list if none are available
    if len(versions) > 1:
        # Get the latest non-deleted version
        query = f"SELECT * FROM c WHERE c.type = 'dataset' AND c.base_name = '{dataset['base_name']}' AND NOT IS_DEFINED(c.is_deleted) ORDER BY c.version DESC"
        latest_versions = list(container.query_items(query=query, enable_cross_partition_query=True))
        if latest_versions:
            return redirect(url_for('datasets.view_dataset', dataset_id=latest_versions[0]['id']))
    
    return redirect(url_for('datasets.list_datasets'))


@datasets_bp.route('/<dataset_id>/restore', methods=['POST'])
@login_required
def restore_dataset(dataset_id):
    """Restore a soft-deleted dataset version"""
    query = f"SELECT * FROM c WHERE c.id = '{dataset_id}'"
    items = list(container.query_items(query=query, enable_cross_partition_query=True))
    
    if not items:
        flash('Dataset not found', 'error')
        return redirect(url_for('datasets.list_datasets'))
    
    dataset = items[0]
    
    if not dataset.get('is_deleted', False):
        flash('This dataset is not deleted', 'warning')
        return redirect(url_for('datasets.view_dataset', dataset_id=dataset_id))
    
    # Remove deletion fields
    del dataset['is_deleted']
    if 'deleted_by' in dataset:
        del dataset['deleted_by']
    if 'deleted_at' in dataset:
        del dataset['deleted_at']
    
    container.upsert_item(dataset)
    
    # Track this activity
    try:
        activity = {
            'id': str(uuid.uuid4()),
            'type': 'activity',
            'username': current_user.username,
            'timestamp': datetime.utcnow().isoformat(),
            'activity_type': 'dataset_restore',
            'message': f"Restored dataset '{dataset['name']}' (version {dataset['version']})",
            'dataset_id': dataset_id
        }
        container.create_item(body=activity)
    except Exception:
        # Don't fail if activity tracking fails
        pass
    
    flash(f"Dataset '{dataset['name']}' version {dataset['version']} has been restored", 'success')
    return redirect(url_for('datasets.view_dataset', dataset_id=dataset_id))
