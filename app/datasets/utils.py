import pytz
from datetime import datetime
from ..cosmos_client import activities_container
import uuid

def convert_to_local_time(datasets, timezone_str='Asia/Calcutta'):
    """Convert dataset timestamps to local timezone"""
    for dataset in datasets:
        if 'created_at' in dataset:
            utc_time = datetime.fromisoformat(dataset['created_at'])
            utcmoment = utc_time.replace(tzinfo=pytz.utc)
            local_format = "%Y-%m-%d %H:%M:%S"
            local_time = utcmoment.astimezone(pytz.timezone(timezone_str))
            dataset['created_at_local'] = local_time.strftime(local_format)
            dataset['created_at'] = dataset['created_at_local']
        
        # Convert file timestamps
        for file_info in dataset.get('files', []):
            if 'uploaded_at' in file_info:
                utc_time = datetime.fromisoformat(file_info['uploaded_at'])
                utcmoment = utc_time.replace(tzinfo=pytz.utc)
                local_time = utcmoment.astimezone(pytz.timezone(timezone_str))
                file_info['uploaded_at_local'] = local_time.strftime(local_format)
                file_info['uploaded_at'] = file_info['uploaded_at_local']

def group_datasets_by_base_name(datasets):
    """Group datasets by their base name to show versions"""
    dataset_groups = {}
    for dataset in datasets:
        base_name = dataset.get('base_name', dataset['name'])
        if base_name not in dataset_groups:
            dataset_groups[base_name] = []
        dataset_groups[base_name].append(dataset)
    return dataset_groups

def log_user_activity(username, activity_type, message, dataset_id=None, file_id=None):
    """Log user activity"""
    try:
        activity = {
            'id': str(uuid.uuid4()),
            'username': username,
            'timestamp': datetime.utcnow().isoformat(),
            'activity_type': activity_type,
            'message': message,
            'dataset_id': dataset_id,
            'file_id': file_id
        }
        activities_container.create_item(body=activity)
        return True
    except Exception:
        return False
