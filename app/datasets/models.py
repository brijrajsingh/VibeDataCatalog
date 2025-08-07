import uuid
from datetime import datetime
from ..cosmos_client import metadata_container
from ..utils import validate_dataset_name, sanitize_dataset_name

class DatasetModel:
    """Dataset data access and business logic"""
    
    @staticmethod
    def get_by_id(dataset_id):
        """Get dataset by ID"""
        query = f"SELECT * FROM c WHERE c.id = '{dataset_id}'"
        items = list(metadata_container.query_items(query=query, enable_cross_partition_query=True))
        return items[0] if items else None
    
    @staticmethod
    def create(name, description, tags, created_by, version=None, parent_id=None, base_name=None):
        """Create a new dataset record"""
        if not parent_id:
            # Validate dataset name for new datasets
            is_valid, error_message = validate_dataset_name(name)
            if not is_valid:
                raise ValueError(f"Invalid dataset name: {error_message}")
            
            # Check for name conflicts when creating brand new datasets
            query = f"SELECT * FROM c WHERE c.name = '{name}' AND NOT IS_DEFINED(c.is_deleted)"
            existing_datasets = list(metadata_container.query_items(query=query, enable_cross_partition_query=True))
            
            if existing_datasets:
                raise ValueError(f"A dataset with the name '{name}' already exists")
            
            base_name = base_name or name
            version = version or 1
        else:
            # For new versions, get base_name from parent
            if not base_name:
                parent_dataset = DatasetModel.get_by_id(parent_id)
                if not parent_dataset:
                    raise ValueError('Parent dataset not found')
                base_name = parent_dataset['base_name']
            
            # Auto-generate version number
            if version is None:
                query = f"SELECT c.version FROM c WHERE c.base_name = '{base_name}'"
                version_items = list(metadata_container.query_items(query=query, enable_cross_partition_query=True))
                versions = [item['version'] for item in version_items if 'version' in item]
                max_version = max(versions) if versions else 0
                version = max_version + 1
            
            # For versioned datasets, construct the name with version
            name = f"{base_name} v{version}"
        
        # Create dataset record
        dataset_id = str(uuid.uuid4())
        dataset = {
            'id': dataset_id,
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
        
        metadata_container.create_item(body=dataset)
        return dataset_id, dataset
    
    @staticmethod
    def list_all(show_deleted=False):
        """List all datasets"""
        if show_deleted:
            query = "SELECT * FROM c ORDER BY c._ts DESC"
        else:
            query = "SELECT * FROM c WHERE NOT IS_DEFINED(c.is_deleted) ORDER BY c._ts DESC"
        
        return list(metadata_container.query_items(query=query, enable_cross_partition_query=True))
    
    @staticmethod
    def get_versions(base_name):
        """Get all versions of a dataset"""
        query = f"SELECT * FROM c WHERE c.base_name = '{base_name}' ORDER BY c.version DESC"
        return list(metadata_container.query_items(query=query, enable_cross_partition_query=True))
    
    @staticmethod
    def get_lineage(dataset):
        """Get lineage information for a dataset"""
        lineage = []
        current = dataset
        while current.get('parent_id'):
            query = f"SELECT * FROM c WHERE c.id = '{current['parent_id']}'"
            parent_items = list(metadata_container.query_items(query=query, enable_cross_partition_query=True))
            if parent_items:
                parent = parent_items[0]
                lineage.append(parent)
                current = parent
            else:
                break
        return lineage
    
    @staticmethod
    def update(dataset):
        """Update a dataset"""
        metadata_container.replace_item(item=dataset['id'], body=dataset)
    
    @staticmethod
    def soft_delete(dataset_id, deleted_by):
        """Soft delete a dataset"""
        dataset = DatasetModel.get_by_id(dataset_id)
        if not dataset:
            raise ValueError('Dataset not found')
        
        dataset['is_deleted'] = True
        dataset['deleted_by'] = deleted_by
        dataset['deleted_at'] = datetime.utcnow().isoformat()
        
        metadata_container.upsert_item(dataset)
        return dataset
    
    @staticmethod
    def restore(dataset_id):
        """Restore a soft-deleted dataset"""
        dataset = DatasetModel.get_by_id(dataset_id)
        if not dataset:
            raise ValueError('Dataset not found')
        
        if not dataset.get('is_deleted', False):
            raise ValueError('Dataset is not deleted')
        
        # Remove deletion fields
        del dataset['is_deleted']
        if 'deleted_by' in dataset:
            del dataset['deleted_by']
        if 'deleted_at' in dataset:
            del dataset['deleted_at']
        
        metadata_container.upsert_item(dataset)
        return dataset
    
    @staticmethod
    def set_production(dataset_id, is_production, user):
        """Set or unset production status"""
        dataset = DatasetModel.get_by_id(dataset_id)
        if not dataset:
            raise ValueError('Dataset not found')
        
        if dataset.get('is_deleted', False):
            raise ValueError('Cannot set production status on deleted datasets')
        
        if is_production:
            # Remove production status from other versions
            query = f"SELECT * FROM c WHERE c.base_name = '{dataset['base_name']}' AND c.is_production = true"
            production_datasets = list(metadata_container.query_items(query=query, enable_cross_partition_query=True))
            
            for prod_dataset in production_datasets:
                if prod_dataset['id'] != dataset_id:
                    prod_dataset['is_production'] = False
                    if 'production_set_by' in prod_dataset:
                        del prod_dataset['production_set_by']
                    if 'production_set_at' in prod_dataset:
                        del prod_dataset['production_set_at']
                    metadata_container.upsert_item(prod_dataset)
            
            # Set current dataset as production
            dataset['is_production'] = True
            dataset['production_set_by'] = user
            dataset['production_set_at'] = datetime.utcnow().isoformat()
        else:
            dataset['is_production'] = False
            if 'production_set_by' in dataset:
                del dataset['production_set_by']
            if 'production_set_at' in dataset:
                del dataset['production_set_at']
        
        metadata_container.upsert_item(dataset)
        return dataset
    
    @staticmethod
    def get_all_tags():
        """Get all unique tags used in datasets"""
        query = "SELECT c.tags FROM c WHERE NOT IS_DEFINED(c.is_deleted)"
        datasets = list(metadata_container.query_items(query=query, enable_cross_partition_query=True))
        
        all_tags = set()
        for dataset in datasets:
            tags = dataset.get('tags', [])
            for tag in tags:
                all_tags.add(tag.strip())
        
        return sorted(list(all_tags))
