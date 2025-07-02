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

# Extract reusable business logic functions
def create_dataset_record(name, description, tags, created_by, version=None, parent_id=None, base_name=None):
    """Create a new dataset record - reusable function for both new datasets and new versions"""
    
    # For new versions, we don't check for existing name conflicts since they can have same base_name
    if not parent_id:
        # Only check for name conflicts when creating brand new datasets (not versions)
        query = f"SELECT * FROM c WHERE c.type = 'dataset' AND c.name = '{name}' AND NOT IS_DEFINED(c.is_deleted)"
        existing_datasets = list(container.query_items(query=query, enable_cross_partition_query=True))
        
        if existing_datasets:
            raise ValueError(f"A dataset with the name '{name}' already exists")
        
        # For new datasets, base_name is same as name and version starts at 1
        base_name = base_name or name
        version = version or 1
    else:
        # For new versions, we need the base_name from parent or provided
        if not base_name:
            parent_dataset = get_dataset_by_id(parent_id)
            if not parent_dataset:
                raise ValueError('Parent dataset not found')
            base_name = parent_dataset['base_name']
        
        # Auto-generate version number for new versions
        if version is None:
            # Get all versions to find the maximum version number
            query = f"SELECT c.version FROM c WHERE c.type = 'dataset' AND c.base_name = '{base_name}'"
            version_items = list(container.query_items(query=query, enable_cross_partition_query=True))
            
            # Find the maximum version
            versions = [item['version'] for item in version_items if 'version' in item]
            max_version = max(versions) if versions else 0
            version = max_version + 1
    
    # Create a new dataset record
    dataset_id = str(uuid.uuid4())
    dataset = {
        'id': dataset_id,
        'type': 'dataset',
        'name': name,
        'base_name': base_name,
        'description': description,
        'tags': tags,
        'version': version,
        'is_production': False,
        'created_by': created_by,
        'created_at': datetime.utcnow().isoformat(),
        'files': [],
        'parent_id': parent_id
    }
    
    container.create_item(body=dataset)
    return dataset_id, dataset

def get_dataset_by_id(dataset_id):
    """Get dataset by ID - reusable function"""
    query = f"SELECT * FROM c WHERE c.id = '{dataset_id}'"
    items = list(container.query_items(query=query, enable_cross_partition_query=True))
    return items[0] if items else None

def upload_file_to_dataset(dataset_id, file, uploaded_by, description='', tags=None):
    """Upload file to dataset - reusable function"""
    dataset = get_dataset_by_id(dataset_id)
    if not dataset:
        raise ValueError('Dataset not found')
    
    if not file or file.filename == '':
        raise ValueError('No file provided')
    
    # Save file to Azure Blob Storage
    filename = file.filename
    file_id = str(uuid.uuid4())
    blob_path = f"{dataset['base_name']}/{dataset['version']}/{file_id}_{filename}"
    
    # Upload to blob storage
    blob_client = blob_service_client.get_blob_client(container=AZURE_BLOB_CONTAINER, blob=blob_path)
    file.seek(0)
    blob_client.upload_blob(file.read(), overwrite=True)
    
    # Reset file pointer and calculate file size in kilobytes
    file.seek(0, io.SEEK_END)  # Move to the end of the file to get its size
    size_bytes = file.tell()
    file.seek(0)  # Reset pointer for further operations
    size_kb = size_bytes / 1024            
    
    # Create file metadata
    file_info = {
        'id': file_id,
        'filename': filename,
        'blob_path': blob_path,
        'uploaded_by': uploaded_by,
        'uploaded_at': datetime.utcnow().isoformat(),
        'size_bytes': size_bytes,
        'size_kb': round(size_kb, 2),
        'content_type': getattr(file, 'content_type', 'application/octet-stream'),
        'description': description,
        'tags': tags or []
    }
    
    # Update dataset
    if 'files' not in dataset:
        dataset['files'] = []
    
    dataset['files'].append(file_info)
    dataset['updated_at'] = datetime.utcnow().isoformat()
    dataset['updated_by'] = uploaded_by
    
    container.replace_item(item=dataset['id'], body=dataset)
    
    return file_id, file_info

def search_datasets_query(query_term='', show_deleted=False):
    """Search datasets - reusable function"""
    if not query_term:
        return []
    
    # Parse the query for advanced search
    search_parts = query_term.split()
    tag_filters = []
    uploader_filters = []
    name_filters = []
    status_filter = None
    
    for part in search_parts:
        if part.startswith('tag:'):
            tag_filters.append(part[4:].lower())
        elif part.startswith('by:'):
            uploader_filters.append(part[3:].lower())
        elif part == 'status:deleted':
            status_filter = 'deleted'
        elif part == 'status:active':
            status_filter = 'active'
        elif part == 'status:production':
            status_filter = 'production'
        else:
            name_filters.append(part)
    
    # Construct the CosmosDB query
    filters = []
    
    # Handle status filtering
    if status_filter == 'deleted':
        filters.append("IS_DEFINED(c.is_deleted)")
    elif status_filter == 'production':
        filters.append("NOT IS_DEFINED(c.is_deleted) AND c.is_production = true")
    elif status_filter == 'active':
        filters.append("NOT IS_DEFINED(c.is_deleted) AND (NOT IS_DEFINED(c.is_production) OR c.is_production = false)")
    elif not show_deleted:
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
        filters.append("(ARRAY_LENGTH(c.tags) > 0)")
    
    # Combine filters
    main_query = "SELECT * FROM c WHERE c.type = 'dataset'"
    if filters:
        main_query += " AND " + " AND ".join(filters)
    
    # Execute query
    all_datasets = list(container.query_items(query=main_query, enable_cross_partition_query=True))
    
    # Post-query filtering for tags (case-insensitive)
    if has_tag_filter:
        filtered_datasets = []
        for dataset in all_datasets:
            dataset_tags = []
            if 'tags' in dataset and dataset['tags']:
                dataset_tags = [tag.lower() for tag in dataset['tags']]
            
            if all(tag_filter in dataset_tags for tag_filter in tag_filters):
                filtered_datasets.append(dataset)
                
        return filtered_datasets
    else:
        return all_datasets

def get_file_from_dataset(dataset_id, file_id):
    """Get file info from dataset - reusable function"""
    dataset = get_dataset_by_id(dataset_id)
    if not dataset:
        return None, None
    
    for file_info in dataset.get('files', []):
        if file_info['id'] == file_id:
            return dataset, file_info
    
    return dataset, None

def log_user_activity(username, activity_type, message, dataset_id=None, file_id=None):
    """Log user activity - reusable function"""
    try:
        activity = {
            'id': str(uuid.uuid4()),
            'type': 'activity',
            'username': username,
            'timestamp': datetime.utcnow().isoformat(),
            'activity_type': activity_type,
            'message': message,
            'dataset_id': dataset_id,
            'file_id': file_id
        }
        container.create_item(body=activity)
        return True
    except Exception:
        return False

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
        
        try:
            # Create a brand new dataset (no parent), version will default to 1
            dataset_id, dataset = create_dataset_record(
                name=name, 
                description=description, 
                tags=tags, 
                created_by=current_user.username,
                version=None,  # Let function set version=1 for new datasets
                parent_id=None
            )
            log_user_activity(current_user.username, 'dataset_created', f"Created dataset '{name}'", dataset_id)
            flash('Dataset registered successfully', 'success')
            return redirect(url_for('datasets.view_dataset', dataset_id=dataset_id))
        except ValueError as e:
            flash(str(e), 'error')
            return redirect(request.url)
    
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
    dataset = get_dataset_by_id(dataset_id)
    if not dataset:
        flash('Dataset not found', 'error')
        return redirect(url_for('datasets.list_datasets'))
    
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        description = request.form.get('description', '')
        tags = [tag.strip() for tag in request.form.get('tags', '').split(',') if tag.strip()]
        
        try:
            file_id, file_info = upload_file_to_dataset(dataset_id, file, current_user.username, description, tags)
            log_user_activity(current_user.username, 'file_uploaded', f"Uploaded file '{file.filename}' to dataset '{dataset['name']}'", dataset_id, file_id)
            flash('File uploaded successfully', 'success')
            return redirect(url_for('datasets.view_dataset', dataset_id=dataset_id))
        except ValueError as e:
            flash(str(e), 'error')
            return redirect(request.url)
    
    return render_template('datasets/upload.html', dataset=dataset)

@datasets_bp.route('/<dataset_id>/new_version', methods=['GET', 'POST'])
@login_required
def new_version(dataset_id):
    """Create a new version of a dataset"""
    parent_dataset = get_dataset_by_id(dataset_id)
    if not parent_dataset:
        flash('Dataset not found', 'error')
        return redirect(url_for('datasets.list_datasets'))
    
    if request.method == 'POST':
        description = request.form.get('description', parent_dataset['description'])
        tags = [tag.strip() for tag in request.form.get('tags', ','.join(parent_dataset['tags'])).split(',') if tag.strip()]
        
        try:
            # Create a new version using the same function
            # Don't set name yet, will be updated after we know the version number
            new_dataset_id, new_dataset = create_dataset_record(
                name="temp_name",  # Temporary name, will be updated below
                description=description,
                tags=tags,
                created_by=current_user.username,
                version=None,  # Let function auto-calculate the next version number
                parent_id=parent_dataset['id'],
                base_name=parent_dataset['base_name']
            )
            
            # Update the name with the actual version number
            new_dataset['name'] = f"{parent_dataset['base_name']} v{new_dataset['version']}"
            container.replace_item(item=new_dataset['id'], body=new_dataset)
            
            log_user_activity(
                current_user.username, 
                'dataset_version_created', 
                f"Created version {new_dataset['version']} of dataset '{parent_dataset['base_name']}'", 
                new_dataset_id
            )
            flash(f'New dataset version {new_dataset["version"]} created', 'success')
            return redirect(url_for('datasets.view_dataset', dataset_id=new_dataset_id))
        except ValueError as e:
            flash(str(e), 'error')
            return redirect(request.url)
    
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
    
    datasets = search_datasets_query(query_term, show_deleted)
    
    # Convert timestamps to local time
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

@datasets_bp.route('/<dataset_id>/set_production', methods=['POST'])
@login_required
def set_production_status(dataset_id):
    """Set a dataset version as production or remove production status"""
    query = f"SELECT * FROM c WHERE c.id = '{dataset_id}'"
    items = list(container.query_items(query=query, enable_cross_partition_query=True))
    
    if not items:
        flash('Dataset not found', 'error')
        return redirect(url_for('datasets.list_datasets'))
    
    dataset = items[0]
    action = request.form.get('action')  # 'set' or 'unset'
    
    # Cannot set production status on deleted datasets
    if dataset.get('is_deleted', False):
        flash('Cannot set production status on deleted datasets', 'error')
        return redirect(url_for('datasets.view_dataset', dataset_id=dataset_id))
    
    if action == 'set':
        # First, remove production status from any other versions of the same dataset
        query = f"SELECT * FROM c WHERE c.type = 'dataset' AND c.base_name = '{dataset['base_name']}' AND c.is_production = true"
        production_datasets = list(container.query_items(query=query, enable_cross_partition_query=True))
        
        for prod_dataset in production_datasets:
            if prod_dataset['id'] != dataset_id:
                prod_dataset['is_production'] = False
                if 'production_set_by' in prod_dataset:
                    del prod_dataset['production_set_by']
                if 'production_set_at' in prod_dataset:
                    del prod_dataset['production_set_at']
                container.upsert_item(prod_dataset)
        
        # Set current dataset as production
        dataset['is_production'] = True
        dataset['production_set_by'] = current_user.username
        dataset['production_set_at'] = datetime.utcnow().isoformat()
        
        container.upsert_item(dataset)
        
        # Track this activity
        try:
            activity = {
                'id': str(uuid.uuid4()),
                'type': 'activity',
                'username': current_user.username,
                'timestamp': datetime.utcnow().isoformat(),
                'activity_type': 'dataset_production_set',
                'message': f"Set dataset '{dataset['name']}' (version {dataset['version']}) as production",
                'dataset_id': dataset_id
            }
            container.create_item(body=activity)
        except Exception:
            pass
            
        flash(f"Dataset '{dataset['name']}' version {dataset['version']} has been set as production", 'success')
        
    elif action == 'unset':
        dataset['is_production'] = False
        if 'production_set_by' in dataset:
            del dataset['production_set_by']
        if 'production_set_at' in dataset:
            del dataset['production_set_at']
            
        container.upsert_item(dataset)
        
        # Track this activity
        try:
            activity = {
                'id': str(uuid.uuid4()),
                'type': 'activity',
                'username': current_user.username,
                'timestamp': datetime.utcnow().isoformat(),
                'activity_type': 'dataset_production_unset',
                'message': f"Removed production status from dataset '{dataset['name']}' (version {dataset['version']})",
                'dataset_id': dataset_id
            }
            container.create_item(body=activity)
        except Exception:
            pass
            
        flash(f"Production status removed from dataset '{dataset['name']}' version {dataset['version']}", 'success')
    
    return redirect(url_for('datasets.view_dataset', dataset_id=dataset_id))
