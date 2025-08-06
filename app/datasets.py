# This file is kept for backward compatibility
# All functionality has been moved to the datasets package

from .datasets import datasets_bp
from .datasets.models import DatasetModel
from .datasets.files import FileManager
from .datasets.search import DatasetSearch
from .datasets.utils import log_user_activity

# Re-export the main functions that other modules might be importing
create_dataset_record = DatasetModel.create
get_dataset_by_id = DatasetModel.get_by_id
upload_file_to_dataset = FileManager.upload_to_dataset
search_datasets_query = DatasetSearch.search
get_file_from_dataset = FileManager.get_from_dataset

__all__ = [
    'datasets_bp',
    'create_dataset_record',
    'get_dataset_by_id', 
    'upload_file_to_dataset',
    'search_datasets_query',
    'get_file_from_dataset',
    'log_user_activity'
]
