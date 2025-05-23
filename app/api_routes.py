from flask import Blueprint, jsonify, current_app as app, request
from flask_login import login_required, current_user
from azure.cosmos import CosmosClient
import os
from datetime import datetime, timedelta
import uuid

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
    query = "SELECT TOP 10 c.id, c.timestamp, c.username, c.message, c.activity_type FROM c WHERE c.type = 'activity' ORDER BY c._ts DESC"
    activities = list(container.query_items(query=query, enable_cross_partition_query=True))
    
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
