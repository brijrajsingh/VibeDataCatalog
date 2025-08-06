
# CosmosDB Container Structure

## Overview
The application uses three separate CosmosDB containers instead of a single container with type filtering for better performance and organization.

## Container Details

### 1. **users** container
- **Purpose**: Store user account information
- **Partition Key**: `/id`
- **Contains**: User profiles, authentication data, API keys
- **Example Document**:
```json
{
    "id": "user-uuid",
    "username": "john_doe",
    "email": "john@example.com",
    "password": "hashed_password",
    "role": "user",
    "status": "active",
    "api_key": "api-key-uuid"
}
```

### 2. **metadata** container  
- **Purpose**: Store dataset metadata and information
- **Partition Key**: `/id`
- **Contains**: Dataset definitions, file lists, versioning info
- **Example Document**:
```json
{
    "id": "dataset-uuid",
    "name": "Sales Data v2",
    "base_name": "Sales Data",
    "description": "Monthly sales data",
    "tags": ["sales", "analytics"],
    "version": 2,
    "created_by": "john_doe",
    "created_at": "2025-08-05T10:00:00Z",
    "files": [...],
    "parent_id": "parent-dataset-uuid"
}
```

### 3. **activities** container
- **Purpose**: Store user activity logs and audit trails
- **Partition Key**: `/username`
- **Contains**: All user actions, API calls, system events
- **Example Document**:
```json
{
    "id": "activity-uuid", 
    "username": "john_doe",
    "timestamp": "2025-08-05T10:00:00Z",
    "activity_type": "dataset_created",
    "message": "Created dataset 'Sales Data'",
    "dataset_id": "dataset-uuid"
}
```

## Environment Variables

```properties
COSMOSDB_DATABASE=datacatalog-v2
COSMOSDB_USERS_CONTAINER=users
COSMOSDB_METADATA_CONTAINER=metadata  
COSMOSDB_ACTIVITIES_CONTAINER=activities
```

## Benefits of Separate Containers

1. **Performance**: No need for type filtering in queries
2. **Scaling**: Each container can be scaled independently
3. **Partition Strategy**: Optimized partition keys for each data type
4. **Security**: Fine-grained access control per container
5. **Maintenance**: Easier to backup/restore specific data types

## Migration from Single Container

If migrating from the old single-container approach:

1. Run `python setup_containers.py` to create new containers
2. Run `python migrate_data.py` to move data from old container
3. Update application to use new container structure

## Container Access in Code

```python
from .cosmos_client import users_container, metadata_container, activities_container

# Users
users = list(users_container.query_items("SELECT * FROM c"))

# Datasets (stored in metadata container)
datasets = list(metadata_container.query_items("SELECT * FROM c"))

# Activities  
activities = list(activities_container.query_items("SELECT * FROM c"))
```
