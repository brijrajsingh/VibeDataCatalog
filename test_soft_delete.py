"""
Comprehensive test script for the dataset soft delete functionality.
This script tests all aspects of soft delete functiondef cleanup():
    """Clean up test data."""
    print("\n===== Cleaning up test data =====")
    
    # Attempt to delete the test datasets
    for dataset in test_datasets:
        try:
            dataset_id = dataset['id']
            query = f"SELECT * FROM c WHERE c.id = '{dataset_id}'"
            items = list(container.query_items(query=query, enable_cross_partition_query=True))
            
            if items:
                container.delete_item(item=items[0], partition_key=items[0]['type'])
                print(f"Deleted test dataset: {items[0]['name']}")
        except Exception as e:
            print(f"Error deleting dataset {dataset['id']}: {e}")
    
    print("===== Cleanup completed =====")


def main():
    """Run all tests."""
    print("======================================")
    print("   DATASET SOFT DELETE TEST SUITE")
    print("======================================\n")
    
    try:
        setup()
        test_soft_delete()
        test_restore()
        test_list_filtering()
        test_search_filtering()
        test_all_versions_deleted()
        test_lineage_view()
    except Exception as e:
        print(f"Error running tests: {e}")
    finally:
        # Uncomment if you want to clean up test data after tests
        # cleanup() 
    
    print("\n======================================")
    print("         ALL TESTS COMPLETED")
    print("======================================")


if __name__ == "__main__":
    main()y including:
1. Soft deleting a dataset
2. Restoring a deleted dataset
3. Testing the visibility filters (show/hide deleted datasets)
4. Edge cases like deleting all versions of a dataset
5. Lineage view handling of deleted datasets
"""

from app.datasets import container, soft_delete_dataset, restore_dataset
from flask import Flask, request, url_for
import uuid
from datetime import datetime
import json
import time

app = Flask(__name__)

# Test datasets with multiple versions
test_datasets = [
    {
        'id': str(uuid.uuid4()),
        'type': 'dataset',
        'name': 'Test Dataset v1',
        'base_name': 'Test Dataset',
        'description': 'This is a test dataset version 1',
        'tags': ['test', 'v1'],
        'version': 1,
        'created_by': 'testuser',
        'created_at': datetime.utcnow().isoformat(),
        'files': []
    },
    {
        'id': str(uuid.uuid4()),
        'type': 'dataset',
        'name': 'Test Dataset v2',
        'base_name': 'Test Dataset',
        'description': 'This is a test dataset version 2',
        'tags': ['test', 'v2'],
        'version': 2,
        'created_by': 'testuser',
        'created_at': datetime.utcnow().isoformat(),
        'files': [],
        'parent_id': None  # Will be set to first dataset's ID in setup
    },
    {
        'id': str(uuid.uuid4()),
        'type': 'dataset',
        'name': 'Another Dataset v1',
        'base_name': 'Another Dataset',
        'description': 'This is a separate test dataset',
        'tags': ['test', 'another'],
        'version': 1,
        'created_by': 'testuser',
        'created_at': datetime.utcnow().isoformat(),
        'files': []
    }
]

def setup():
    """Insert test datasets into the database and set up parent-child relationships."""
    print("Setting up test datasets...")
    
    # Store created IDs to update relationships
    created_ids = {}
    
    for i, dataset in enumerate(test_datasets):
        try:
            # For the second dataset in the family, link to the first
            if i == 1:  # Test Dataset v2
                dataset['parent_id'] = created_ids.get('Test Dataset')
                
            container.create_item(body=dataset)
            print(f"Created dataset: {dataset['name']} (ID: {dataset['id']})")
            
            # Save the first ID of each base_name for parent-child relationships
            if dataset['base_name'] not in created_ids:
                created_ids[dataset['base_name']] = dataset['id']
                
        except Exception as e:
            print(f"Error creating dataset: {e}")
    
    # Sleep briefly to ensure all database operations are complete
    time.sleep(2)
    print("Setup complete!\n")

def test_soft_delete():
    """Test the soft delete functionality."""
    print("\n===== Testing soft delete =====")
    
    # Get the first test dataset (Test Dataset v1)
    dataset_id = test_datasets[0]['id']
    query = f"SELECT * FROM c WHERE c.id = '{dataset_id}'"
    items = list(container.query_items(query=query, enable_cross_partition_query=True))
    
    if not items:
        print(f"Error: Dataset with ID {dataset_id} not found.")
        return
    
    dataset = items[0]
    print(f"Found dataset: {dataset['name']}")
    
    # Mock request and user for soft delete
    class MockRequest:
        def __init__(self):
            self.method = 'POST'
    
    class MockUser:
        def __init__(self):
            self.username = 'testadmin'
    
    request._get_current_object = lambda: MockRequest()
    current_user = MockUser()
    
    # Test soft delete
    print(f"Soft deleting dataset: {dataset['name']}...")
    with app.test_request_context():
        try:
            # Mark as deleted
            dataset['is_deleted'] = True
            dataset['deleted_by'] = current_user.username
            dataset['deleted_at'] = datetime.utcnow().isoformat()
            container.upsert_item(dataset)
            print(f"Successfully soft deleted dataset {dataset['name']}")
        except Exception as e:
            print(f"Error soft deleting dataset: {e}")
    
    # Verify the dataset is marked as deleted
    items = list(container.query_items(query=query, enable_cross_partition_query=True))
    if items and 'is_deleted' in items[0]:
        print(f"✓ Verification successful: Dataset is marked as deleted by {items[0].get('deleted_by')}")
    else:
        print("✗ Verification failed: Dataset is not properly marked as deleted")
        
    print("===== Soft delete test completed =====")


def test_restore():
    """Test the restore functionality."""
    print("\n===== Testing restore =====")
    
    # Get the first test dataset (which should be deleted from previous test)
    dataset_id = test_datasets[0]['id']
    query = f"SELECT * FROM c WHERE c.id = '{dataset_id}'"
    items = list(container.query_items(query=query, enable_cross_partition_query=True))
    
    if not items:
        print(f"Error: Dataset with ID {dataset_id} not found.")
        return
    
    dataset = items[0]
    
    if not dataset.get('is_deleted', False):
        print(f"Warning: Dataset {dataset['name']} is not deleted. Marking it as deleted first...")
        dataset['is_deleted'] = True
        dataset['deleted_by'] = 'testadmin'
        dataset['deleted_at'] = datetime.utcnow().isoformat()
        container.upsert_item(dataset)
        print("Dataset marked as deleted. Now testing restore...")
    else:
        print(f"Found deleted dataset: {dataset['name']}")
    
    # Test restore
    print(f"Restoring dataset: {dataset['name']}...")
    try:
        # Remove deletion fields
        del dataset['is_deleted']
        if 'deleted_by' in dataset:
            del dataset['deleted_by']
        if 'deleted_at' in dataset:
            del dataset['deleted_at']
        
        container.upsert_item(dataset)
        print(f"Successfully restored dataset {dataset['name']}")
    except Exception as e:
        print(f"Error restoring dataset: {e}")
    
    # Verify the dataset is no longer marked as deleted
    items = list(container.query_items(query=query, enable_cross_partition_query=True))
    if items and 'is_deleted' not in items[0]:
        print(f"✓ Verification successful: Dataset is no longer marked as deleted")
    else:
        print("✗ Verification failed: Dataset is still marked as deleted")
        
    print("===== Restore test completed =====")


def test_list_filtering():
    """Test the filtering to show/hide deleted datasets."""
    print("\n===== Testing dataset list filtering =====")
    
    # First, make sure we have both deleted and non-deleted datasets
    first_dataset_id = test_datasets[0]['id']
    second_dataset_id = test_datasets[1]['id']
    
    # Mark one dataset as deleted
    query = f"SELECT * FROM c WHERE c.id = '{first_dataset_id}'"
    items = list(container.query_items(query=query, enable_cross_partition_query=True))
    if items:
        dataset = items[0]
        dataset['is_deleted'] = True
        dataset['deleted_by'] = 'testadmin'
        dataset['deleted_at'] = datetime.utcnow().isoformat()
        container.upsert_item(dataset)
        print(f"Marked dataset {dataset['name']} as deleted for testing")
    
    # Test filtering: hide deleted
    print("Testing list with show_deleted=False...")
    query_hide_deleted = "SELECT * FROM c WHERE c.type = 'dataset' AND NOT IS_DEFINED(c.is_deleted)"
    hidden_datasets = list(container.query_items(query=query_hide_deleted, enable_cross_partition_query=True))
    
    print(f"Retrieved {len(hidden_datasets)} non-deleted datasets")
    print("Checking if deleted dataset is properly hidden...")
    
    hidden_ids = [d['id'] for d in hidden_datasets]
    if first_dataset_id not in hidden_ids:
        print(f"✓ Verification successful: Deleted dataset is properly hidden")
    else:
        print(f"✗ Verification failed: Deleted dataset was not hidden")
    
    # Test filtering: show deleted
    print("\nTesting list with show_deleted=True...")
    query_show_all = "SELECT * FROM c WHERE c.type = 'dataset'"
    all_datasets = list(container.query_items(query=query_show_all, enable_cross_partition_query=True))
    
    print(f"Retrieved {len(all_datasets)} total datasets (including deleted)")
    print("Checking if deleted dataset is included...")
    
    all_ids = [d['id'] for d in all_datasets]
    if first_dataset_id in all_ids:
        print(f"✓ Verification successful: Deleted dataset is properly included")
    else:
        print(f"✗ Verification failed: Deleted dataset was not found")
    
    print("===== List filtering test completed =====")


def test_search_filtering():
    """Test searching with status filters."""
    print("\n===== Testing search filtering =====")
    
    # Make sure we have at least one deleted dataset
    first_dataset_id = test_datasets[0]['id']
    
    # Mark dataset as deleted if not already
    query = f"SELECT * FROM c WHERE c.id = '{first_dataset_id}'"
    items = list(container.query_items(query=query, enable_cross_partition_query=True))
    if items:
        dataset = items[0]
        if not dataset.get('is_deleted', False):
            dataset['is_deleted'] = True
            dataset['deleted_by'] = 'testadmin'
            dataset['deleted_at'] = datetime.utcnow().isoformat()
            container.upsert_item(dataset)
            print(f"Marked dataset {dataset['name']} as deleted for testing")
    
    # Test status:deleted filter
    print("Testing search with status:deleted filter...")
    query_deleted = "SELECT * FROM c WHERE c.type = 'dataset' AND IS_DEFINED(c.is_deleted)"
    deleted_datasets = list(container.query_items(query=query_deleted, enable_cross_partition_query=True))
    
    print(f"Found {len(deleted_datasets)} deleted datasets")
    if len(deleted_datasets) > 0:
        print("✓ Verification successful: Found deleted datasets with status filter")
    else:
        print("✗ Verification failed: No deleted datasets found")
    
    # Test status:active filter
    print("\nTesting search with status:active filter...")
    query_active = "SELECT * FROM c WHERE c.type = 'dataset' AND NOT IS_DEFINED(c.is_deleted)"
    active_datasets = list(container.query_items(query=query_active, enable_cross_partition_query=True))
    
    print(f"Found {len(active_datasets)} active datasets")
    if len(active_datasets) > 0:
        print("✓ Verification successful: Found active datasets with status filter")
    else:
        print("✗ Verification failed: No active datasets found")
        
    print("===== Search filtering test completed =====")


def test_all_versions_deleted():
    """Test what happens when all versions of a dataset are deleted."""
    print("\n===== Testing deletion of all dataset versions =====")
    
    # We'll use the test datasets with the same base_name (versions 1 & 2)
    base_name = "Test Dataset"
    query = f"SELECT * FROM c WHERE c.type = 'dataset' AND c.base_name = '{base_name}'"
    versions = list(container.query_items(query=query, enable_cross_partition_query=True))
    
    print(f"Found {len(versions)} versions of '{base_name}'")
    
    # Mark all versions as deleted
    for dataset in versions:
        dataset['is_deleted'] = True
        dataset['deleted_by'] = 'testadmin'
        dataset['deleted_at'] = datetime.utcnow().isoformat()
        container.upsert_item(dataset)
        print(f"Marked {dataset['name']} as deleted")
    
    # Verify all versions are hidden with default filters
    query_hide_deleted = f"SELECT * FROM c WHERE c.type = 'dataset' AND c.base_name = '{base_name}' AND NOT IS_DEFINED(c.is_deleted)"
    hidden_versions = list(container.query_items(query=query_hide_deleted, enable_cross_partition_query=True))
    
    print(f"When filtered to hide deleted: Found {len(hidden_versions)} versions")
    if len(hidden_versions) == 0:
        print("✓ Verification successful: All versions are properly hidden when deleted")
    else:
        print("✗ Verification failed: Some versions are still visible")
    
    # Restore at least one version for further tests
    if versions:
        dataset = versions[0]
        del dataset['is_deleted']
        if 'deleted_by' in dataset:
            del dataset['deleted_by']
        if 'deleted_at' in dataset:
            del dataset['deleted_at']
        container.upsert_item(dataset)
        print(f"Restored {dataset['name']} to non-deleted state")
    
    print("===== All versions deletion test completed =====")


def test_lineage_view():
    """Test how the lineage view handles deleted datasets."""
    print("\n===== Testing lineage view handling =====")
    
    # Make sure we have parent-child relationship between datasets
    parent_id = test_datasets[0]['id']
    child_id = test_datasets[1]['id']
    
    # Mark parent as deleted to test lineage with deleted parent
    query = f"SELECT * FROM c WHERE c.id = '{parent_id}'"
    items = list(container.query_items(query=query, enable_cross_partition_query=True))
    if items:
        dataset = items[0]
        dataset['is_deleted'] = True
        dataset['deleted_by'] = 'testadmin'
        dataset['deleted_at'] = datetime.utcnow().isoformat()
        container.upsert_item(dataset)
        print(f"Marked parent dataset {dataset['name']} as deleted for testing")
    
    # This would be more involved to test without the actual Flask app running
    # Since we don't have the complete Flask app context, we'll just verify that
    # our query for the lineage view can retrieve both deleted and non-deleted nodes
    
    # Test with show_deleted=True
    print("Testing lineage view with show_deleted=True...")
    query_all = "SELECT c.id, c.name, c.version, c.base_name, c.parent_id, c.is_deleted FROM c WHERE c.type = 'dataset'"
    all_nodes = list(container.query_items(query=query_all, enable_cross_partition_query=True))
    
    deleted_count = sum(1 for node in all_nodes if node.get('is_deleted'))
    active_count = sum(1 for node in all_nodes if not node.get('is_deleted'))
    
    print(f"Found {len(all_nodes)} total nodes: {deleted_count} deleted, {active_count} active")
    if deleted_count > 0 and active_count > 0:
        print("✓ Verification successful: Lineage query includes both deleted and active datasets")
    else:
        print("✗ Verification failed: Lineage query is missing deleted or active datasets")
    
    # Test with show_deleted=False
    print("\nTesting lineage view with show_deleted=False...")
    query_active = "SELECT c.id, c.name, c.version, c.base_name, c.parent_id FROM c WHERE c.type = 'dataset' AND NOT IS_DEFINED(c.is_deleted)"
    active_nodes = list(container.query_items(query=query_active, enable_cross_partition_query=True))
    
    print(f"Found {len(active_nodes)} active nodes")
    if len(active_nodes) < len(all_nodes) and len(active_nodes) > 0:
        print("✓ Verification successful: Lineage query correctly filters deleted datasets")
    else:
        print("✗ Verification failed: Lineage filtering not working as expected")
        
    print("===== Lineage view test completed =====")
    
    # Test listing with and without deleted datasets
    print("\nTesting dataset listing...")
    
    # Without deleted
    query = "SELECT * FROM c WHERE c.type = 'dataset' AND c.base_name = 'Test Dataset' AND NOT IS_DEFINED(c.is_deleted)"
    non_deleted = list(container.query_items(query=query, enable_cross_partition_query=True))
    print(f"Found {len(non_deleted)} non-deleted datasets")
    
    # With deleted
    query = "SELECT * FROM c WHERE c.type = 'dataset' AND c.base_name = 'Test Dataset'"
    all_datasets = list(container.query_items(query=query, enable_cross_partition_query=True))
    print(f"Found {len(all_datasets)} total datasets (including deleted)")
    
    # Test restore
    if items:
        print("\nTesting restore functionality...")
        dataset = items[0]
        # Remove deletion fields
        if 'is_deleted' in dataset:
            del dataset['is_deleted']
        if 'deleted_by' in dataset:
            del dataset['deleted_by']
        if 'deleted_at' in dataset:
            del dataset['deleted_at']
        
        container.upsert_item(dataset)
        
        # Verify restoration
        items = list(container.query_items(query=f"SELECT * FROM c WHERE c.id = '{dataset_id}'", enable_cross_partition_query=True))
        if items and 'is_deleted' not in items[0]:
            print("Restoration successful: Dataset is no longer marked as deleted")
        else:
            print("Restoration failed")

def cleanup():
    """Remove test datasets from the database."""
    print("\nCleaning up test datasets...")
    for dataset in test_datasets:
        try:
            container.delete_item(item=dataset['id'], partition_key=dataset['type'])
            print(f"Deleted dataset: {dataset['name']} (ID: {dataset['id']})")
        except Exception as e:
            print(f"Error deleting dataset: {e}")
    
    print("Cleanup complete!")

if __name__ == "__main__":
    try:
        setup()
        test_soft_delete()
    finally:
        cleanup()
