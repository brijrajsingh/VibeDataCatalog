from flask import Blueprint, jsonify, current_app as app, request
from flask_login import login_required, current_user
from azure.cosmos import CosmosClient
import os
from datetime import datetime, timedelta
import uuid

import pytz

from .api_auth import api_key_required, get_current_api_user
from werkzeug.utils import secure_filename

# Azure Configuration
ENDPOINT = os.environ.get("COSMOSDB_ENDPOINT")
KEY = os.environ.get("COSMOSDB_KEY")
DATABASE_NAME = os.environ.get("COSMOSDB_DATABASE")
CONTAINER_NAME = os.environ.get("COSMOSDB_CONTAINER")

# Initialize CosmosClient
client = CosmosClient(ENDPOINT, credential=KEY)
database = client.get_database_client(DATABASE_NAME)
container = database.get_container_client(CONTAINER_NAME)

# Blueprint for API routes
api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/recent_datasets')
@login_required
def get_recent_datasets():
    """Get the most recently created datasets"""
    query = "SELECT TOP 5 c.id, c.name, c.description, c.version, c.tags, c.created_at FROM c WHERE c.type = 'dataset' ORDER BY c._ts DESC"
    datasets = list(container.query_items(query=query, enable_cross_partition_query=True))
    
    return jsonify({'datasets': datasets})

@api_bp.route('/activities')
@login_required
def get_activities():
    """Get the most recent activities across all users"""
    browser_timezone = request.args.get('timezone', 'Asia/Calcutta')  # Default to Asia/Calcutta timezone
    query = "SELECT TOP 10 c.id, c.timestamp, c.username, c.message, c.activity_type FROM c WHERE c.type = 'activity' ORDER BY c._ts DESC"
    activities = list(container.query_items(query=query, enable_cross_partition_query=True))
    """convert field timestamp to the browser timezone, timestamp is in UTC""" 
    for activity in activities:
        activity['timestamp'] = datetime.fromisoformat(activity['timestamp']).astimezone().isoformat()
        utc_time = datetime.fromisoformat(activity['timestamp'])
        utcmoment = utc_time.replace(tzinfo=pytz.utc)
        localFormat = "%Y-%m-%d %H:%M:%S"            
        local_time = utcmoment.astimezone(pytz.timezone(browser_timezone))
        activity['timestamp_local']= local_time.strftime(localFormat)
        activity['timestamp'] = activity['timestamp_local']  # Update created_at with local time
    
    
    return jsonify({'activities': activities})

@api_bp.route('/my_datasets')
@login_required
def get_my_datasets():
    """Get the current user's datasets"""
    query = f"SELECT c.id, c.name, c.version, c.files, c.created_at FROM c WHERE c.type = 'dataset' AND c.created_by = '{current_user.username}' ORDER BY c._ts DESC"
    datasets = list(container.query_items(query=query, enable_cross_partition_query=True))
    
    return jsonify({'datasets': datasets})

@api_bp.route('/my_activity')
@login_required
def get_my_activity():
    """Get the current user's activity"""
    query = f"SELECT TOP 20 c.id, c.timestamp, c.message, c.activity_type FROM c WHERE c.type = 'activity' AND c.username = '{current_user.username}' ORDER BY c._ts DESC"
    activities = list(container.query_items(query=query, enable_cross_partition_query=True))
    
    return jsonify({'activities': activities})

@api_bp.route('/tags')
@login_required
def get_tags():
    """Get all tags and their frequency"""
    query = "SELECT c.tags FROM c WHERE c.type = 'dataset'"
    results = list(container.query_items(query=query, enable_cross_partition_query=True))
    
    # Count tag frequency
    tag_counts = {}
    for result in results:
        tags = result.get('tags', [])
        for tag in tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
    
    return jsonify({'tags': tag_counts})

@api_bp.route('/dataset_stats')
@login_required
def get_dataset_stats():
    """Get dataset creation statistics by month"""
    # Get datasets created in the last 6 months
    six_months_ago = (datetime.utcnow() - timedelta(days=180)).isoformat()
    query = f"SELECT c.id, c.created_at FROM c WHERE c.type = 'dataset' AND c.created_at >= '{six_months_ago}'"
    datasets = list(container.query_items(query=query, enable_cross_partition_query=True))
    
    # Group by month
    months = {}
    for dataset in datasets:
        created_at = dataset.get('created_at', '')
        if created_at:
            month = created_at[:7]  # Format: YYYY-MM
            months[month] = months.get(month, 0) + 1
    
    # Sort by month
    sorted_months = sorted(months.items())
    labels = [m[0] for m in sorted_months]
    values = [m[1] for m in sorted_months]
    
    return jsonify({'labels': labels, 'values': values})

@api_bp.route('/track_activity', methods=['POST'])
@login_required
def track_activity():
    """Track user activity"""
    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    activity = {
        'id': str(uuid.uuid4()),
        'type': 'activity',
        'username': current_user.username,
        'timestamp': datetime.utcnow().isoformat(),
        'activity_type': data.get('activity_type'),
        'message': data.get('message'),
        'dataset_id': data.get('dataset_id'),
        'file_id': data.get('file_id')
    }
    
    container.create_item(body=activity)
    
    return jsonify({'status': 'success'})

@api_bp.route('/file_direct_link/<dataset_id>/<file_id>')
@login_required
def get_file_direct_link_api(dataset_id, file_id):
    """Get a direct link to a file with a 5-hour SAS token"""
    # Get dataset information
    query = f"SELECT * FROM c WHERE c.id = '{dataset_id}'"
    items = list(container.query_items(query=query, enable_cross_partition_query=True))
    
    if not items:
        return jsonify({'error': 'Dataset not found'}), 404
    
    dataset = items[0]
    
    # Find the file
    file_info = None
    for file in dataset['files']:
        if file['id'] == file_id:
            file_info = file
            break
    
    if not file_info:
        return jsonify({'error': 'File not found'}), 404
    
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
            'activity_type': 'file_direct_link',
            'message': f"Generated direct link for file '{file_info['filename']}' from dataset '{dataset['name']}'",
            'dataset_id': dataset_id,
            'file_id': file_id
        }
        container.create_item(body=activity)
    except Exception:
        # Don't fail if activity tracking fails
        pass
    
    return jsonify({'url': blob_url, 'filename': file_info['filename'], 'valid_hours': 5})

# Import the reusable functions from datasets module
from .datasets import (
    create_dataset_record, 
    get_dataset_by_id, 
    upload_file_to_dataset, 
    search_datasets_query,
    get_file_from_dataset,
    log_user_activity,
    container  # Import the container for other queries
)

@api_bp.route('/datasets', methods=['GET'])
@api_key_required
def api_get_datasets():
    """API endpoint to get datasets (API key authenticated)"""
    user = get_current_api_user()
    
    # Use the same query logic as the web interface
    query = "SELECT c.id, c.name, c.description, c.version, c.tags, c.created_at, c.created_by FROM c WHERE c.type = 'dataset' AND NOT IS_DEFINED(c.is_deleted) ORDER BY c._ts DESC"
    datasets = list(container.query_items(query=query, enable_cross_partition_query=True))
    
    # Log this API access
    log_user_activity(user.username, 'api_datasets_list', "Listed datasets via API")
    
    return jsonify({'datasets': datasets, 'count': len(datasets)})

@api_bp.route('/datasets', methods=['POST'])
@api_key_required
def api_create_dataset():
    """API endpoint to create a new dataset (API key authenticated)"""
    user = get_current_api_user()
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    required_fields = ['name', 'description', 'tags']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    try:
        # Determine if this is a new dataset or a new version
        is_new_version = data.get('parent_id') is not None
        
        if is_new_version:
            # For new versions, don't require version field - it will be auto-calculated
            dataset_id, dataset = create_dataset_record(
                name="temp_name",  # Will be updated with proper version name
                description=data['description'],
                tags=data['tags'] if isinstance(data['tags'], list) else [data['tags']],
                created_by=user.username,
                version=None,  # Auto-calculate version number
                parent_id=data['parent_id'],
                base_name=data.get('base_name')  # Should be provided or will be derived from parent
            )
            
            # Update name with version number if it was a new version
            if data.get('parent_id'):
                parent_dataset = get_dataset_by_id(data['parent_id'])
                if parent_dataset:
                    dataset['name'] = f"{dataset['base_name']} v{dataset['version']}"
                    container.replace_item(item=dataset['id'], body=dataset)
        else:
            # For brand new datasets, version starts at 1
            dataset_id, dataset = create_dataset_record(
                name=data['name'],
                description=data['description'],
                tags=data['tags'] if isinstance(data['tags'], list) else [data['tags']],
                created_by=user.username,
                version=data.get('version', 1),  # Default to 1 for new datasets
                parent_id=None
            )
        
        # Log this activity using the same function
        activity_message = f"Created dataset '{dataset['name']}' via API"
        if is_new_version:
            activity_message = f"Created version {dataset['version']} of dataset '{dataset['base_name']}' via API"
            
        log_user_activity(
            username=user.username,
            activity_type='api_dataset_created',
            message=activity_message,
            dataset_id=dataset_id
        )
        
        return jsonify({
            'success': True, 
            'dataset_id': dataset_id, 
            'dataset_name': dataset['name'],
            'version': dataset['version'],
            'message': f'Dataset created successfully with version {dataset["version"]}'
        }), 201
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'Failed to create dataset: {str(e)}'}), 500

@api_bp.route('/datasets/<dataset_id>', methods=['GET'])
@api_key_required
def api_get_dataset(dataset_id):
    """API endpoint to get a specific dataset (API key authenticated)"""
    user = get_current_api_user()
    
    # Reuse the same function as the web interface
    dataset = get_dataset_by_id(dataset_id)
    if not dataset:
        return jsonify({'error': 'Dataset not found'}), 404
    
    # Log this API access using the same function
    log_user_activity(
        username=user.username,
        activity_type='api_dataset_accessed',
        message=f"Accessed dataset '{dataset['name']}' via API",
        dataset_id=dataset_id
    )
    
    return jsonify({'dataset': dataset})

@api_bp.route('/datasets/search', methods=['GET'])
@api_key_required
def api_search_datasets():
    """API endpoint to search datasets (API key authenticated)"""
    user = get_current_api_user()
    query_text = request.args.get('q', '')
    
    # Reuse the same search function as the web interface
    datasets = search_datasets_query(query_text, show_deleted=False)
    
    # Log this API search using the same function
    log_user_activity(
        username=user.username,
        activity_type='api_datasets_search',
        message=f"Searched datasets via API: '{query_text}'"
    )
    
    return jsonify({
        'datasets': datasets, 
        'count': len(datasets), 
        'query': query_text
    })

@api_bp.route('/datasets/<dataset_id>/files', methods=['POST'])
@api_key_required
def api_upload_file(dataset_id):
    """API endpoint to upload a file to a dataset (API key authenticated)"""
    user = get_current_api_user()
    
    # Check if dataset exists using the same function
    dataset = get_dataset_by_id(dataset_id)
    if not dataset:
        return jsonify({'error': 'Dataset not found'}), 404
    
    # Check permissions
    if dataset['created_by'] != user.username:
        return jsonify({'error': 'Permission denied. You can only upload files to your own datasets.'}), 403
    
    # Check if file is in request
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    description = request.form.get('description', '')
    tags = request.form.get('tags', '').split(',') if request.form.get('tags') else []
    tags = [tag.strip() for tag in tags if tag.strip()]
    
    try:
        # Reuse the same upload function as the web interface
        file_id, file_info = upload_file_to_dataset(
            dataset_id=dataset_id,
            file=file,
            uploaded_by=user.username,
            description=description,
            tags=tags
        )
        
        # Log this activity using the same function
        log_user_activity(
            username=user.username,
            activity_type='api_file_uploaded',
            message=f"Uploaded file '{file_info['filename']}' to dataset '{dataset['name']}' via API",
            dataset_id=dataset_id,
            file_id=file_id
        )
        
        return jsonify({
            'success': True,
            'message': 'File uploaded successfully',
            'file_id': file_id,
            'filename': file_info['filename'],
            'size': file_info['size_bytes'],
            'dataset_id': dataset_id
        }), 201
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'Failed to upload file: {str(e)}'}), 500

@api_bp.route('/datasets/<dataset_id>/files', methods=['GET'])
@api_key_required
def api_list_files(dataset_id):
    """API endpoint to list files in a dataset (API key authenticated)"""
    user = get_current_api_user()
    
    # Reuse the same function as the web interface
    dataset = get_dataset_by_id(dataset_id)
    if not dataset:
        return jsonify({'error': 'Dataset not found'}), 404
    
    files = dataset.get('files', [])
    
    # Log this API access using the same function
    log_user_activity(
        username=user.username,
        activity_type='api_files_listed',
        message=f"Listed files in dataset '{dataset['name']}' via API",
        dataset_id=dataset_id
    )
    
    return jsonify({
        'dataset_id': dataset_id,
        'dataset_name': dataset['name'],
        'files': files,
        'file_count': len(files)
    })

@api_bp.route('/datasets/<dataset_id>/files/<file_id>/download', methods=['GET'])
@api_key_required
def api_download_file(dataset_id, file_id):
    """API endpoint to get download URL for a file (API key authenticated)"""
    user = get_current_api_user()
    
    # Reuse the same function as the web interface
    dataset, file_info = get_file_from_dataset(dataset_id, file_id)
    if not dataset:
        return jsonify({'error': 'Dataset not found'}), 404
    
    if not file_info:
        return jsonify({'error': 'File not found'}), 404
    
    # Generate download URL using the same utility function
    from .utils import generate_blob_sas_url
    download_url = generate_blob_sas_url(file_info['blob_path'], hours_valid=1)
    
    # Log this activity using the same function
    log_user_activity(
        username=user.username,
        activity_type='api_file_downloaded',
        message=f"Downloaded file '{file_info['filename']}' from dataset '{dataset['name']}' via API",
        dataset_id=dataset_id,
        file_id=file_id
    )
    
    return jsonify({
        'download_url': download_url,
        'filename': file_info['filename'],
        'size_bytes': file_info['size_bytes'],
        'size_kb': file_info['size_kb'],
        'content_type': file_info.get('content_type', 'application/octet-stream'),
        'valid_hours': 1,
        'expires_at': (datetime.utcnow() + timedelta(hours=1)).isoformat()
    })
