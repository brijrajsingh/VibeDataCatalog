import uuid
from datetime import datetime
from azure.storage.blob import BlobServiceClient
import os
import io
from ..cosmos_client import metadata_container
from ..utils import blob_service_client, AZURE_BLOB_CONTAINER
from .models import DatasetModel

class FileManager:
    """Handle file operations for datasets"""
    
    @staticmethod
    def upload_to_dataset(dataset_id, file, uploaded_by, description='', tags=None):
        """Upload file to dataset"""
        dataset = DatasetModel.get_by_id(dataset_id)
        if not dataset:
            raise ValueError('Dataset not found')
        
        if not file or file.filename == '':
            raise ValueError('No file provided')
        
        # Generate file paths
        filename = file.filename
        file_id = str(uuid.uuid4())
        blob_path = f"{dataset['base_name']}/{dataset['version']}/{file_id}_{filename}"
        
        # Upload to blob storage
        blob_client = blob_service_client.get_blob_client(container=AZURE_BLOB_CONTAINER, blob=blob_path)
        file.seek(0)
        blob_client.upload_blob(file.read(), overwrite=True)
        
        # Calculate file size
        file.seek(0, io.SEEK_END)
        size_bytes = file.tell()
        file.seek(0)
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
        
        DatasetModel.update(dataset)
        
        return file_id, file_info
    
    @staticmethod
    def get_from_dataset(dataset_id, file_id):
        """Get file info from dataset"""
        dataset = DatasetModel.get_by_id(dataset_id)
        if not dataset:
            return None, None
        
        for file_info in dataset.get('files', []):
            if file_info['id'] == file_id:
                return dataset, file_info
        
        return dataset, None
