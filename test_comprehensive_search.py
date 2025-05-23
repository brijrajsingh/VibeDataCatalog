"""
Comprehensive search functionality test script for the data catalog application.

This script tests the following search capabilities:
- Name search (case-insensitive)
- Description search (case-insensitive)
- Tag search (case-insensitive)
- Uploader search (case-insensitive)
- Combinations of multiple search criteria
"""

# Sample test data
sample_datasets = [
    {
        "id": "1",
        "type": "dataset",
        "name": "Sales Data 2023",
        "description": "Monthly sales figures for 2023",
        "created_by": "John",  # Note the uppercase
        "tags": ["Sales", "monthly", "2023"]  # Mixed case tags
    },
    {
        "id": "2",
        "type": "dataset",
        "name": "Customer Analysis Report",
        "description": "Detailed ANALYSIS of customer segments",  # "ANALYSIS" in uppercase
        "created_by": "sarah",  # All lowercase
        "tags": ["customers", "ANALYSIS", "Marketing"]  # Mixed case tags
    },
    {
        "id": "3",
        "type": "dataset",
        "name": "Product Inventory",
        "description": "Current inventory levels for all product categories",
        "created_by": "Mike",  # Capitalized
        "tags": ["inventory", "products"]  # All lowercase tags
    }
]

# Test cases for different search types
test_cases = [
    # Name searches
    "sales",                 # Should match dataset 1
    "CUSTOMER",              # Should match dataset 2 (case-insensitive)
    "product inventory",     # Should match dataset 3 (exact match)
    "nonexistent",           # Should match no datasets
    
    # Description searches
    "monthly",               # Should match dataset 1
    "ANALYSIS",              # Should match dataset 2 (case-insensitive)
    "product categories",    # Should match dataset 3
    
    # Tag searches
    "tag:sales",             # Should match dataset 1 (case-insensitive)
    "tag:MONTHLY",           # Should match dataset 1 (case-insensitive)
    "tag:analysis",          # Should match dataset 2 (case-insensitive)
    "tag:inventory",         # Should match dataset 3 (case-insensitive)
    
    # Uploader searches
    "by:john",               # Should match dataset 1 (case-insensitive)
    "by:SARAH",              # Should match dataset 2 (case-insensitive)
    "by:mike",               # Should match dataset 3 (case-insensitive)
    
    # Combined searches
    "sales tag:monthly",     # Should match dataset 1 (both criteria)
    "analysis by:sarah",     # Should match dataset 2 (both criteria)
    "tag:inventory by:mike", # Should match dataset 3 (both criteria)
    "tag:sales tag:analysis",# Should match no datasets (no dataset has both tags)
    "analysis tag:sales",    # Should match no datasets (mixed criteria that don't match)
    "sales by:sarah"         # Should match no datasets (mixed criteria that don't match)
]

def test_search_filter():
    """Test the search filter logic."""
    print("Testing comprehensive search functionality...")
    print("============================================")

    for query in test_cases:
        print(f"\nQuery: '{query}'")
        
        # Parse the query similar to the actual implementation
        search_parts = query.split()
        tag_filters = []
        uploader_filters = []
        name_filters = []
        
        for part in search_parts:
            if part.startswith('tag:'):
                tag_filters.append(part[4:].lower())  # Store lowercase version of tag
            elif part.startswith('by:'):
                uploader_filters.append(part[3:].lower())  # Store lowercase version of uploader
            else:
                name_filters.append(part)
        
        # Initial dataset list
        filtered_datasets = sample_datasets.copy()
        
        # Filter by name and description
        if name_filters:
            name_filtered = []
            for dataset in filtered_datasets:
                # Check if any of the name filters match the name or description
                if any(name.lower() in dataset['name'].lower() for name in name_filters) or \
                   any(name.lower() in dataset['description'].lower() for name in name_filters):
                    name_filtered.append(dataset)
            filtered_datasets = name_filtered
        
        # Filter by uploader
        if uploader_filters:
            uploader_filtered = []
            for dataset in filtered_datasets:
                if dataset['created_by'].lower() in [u.lower() for u in uploader_filters]:
                    uploader_filtered.append(dataset)
            filtered_datasets = uploader_filtered
        
        # Filter by tags
        if tag_filters:
            tag_filtered = []
            for dataset in filtered_datasets:
                # Convert all dataset tags to lowercase
                dataset_tags = [tag.lower() for tag in dataset.get('tags', [])]
                # Check if all requested tag filters are present in this dataset's tags
                if all(tag_filter in dataset_tags for tag_filter in tag_filters):
                    tag_filtered.append(dataset)
            filtered_datasets = tag_filtered
        
        # Output results
        matched_names = [d["name"] for d in filtered_datasets]
        print(f"Found {len(filtered_datasets)} dataset(s): {matched_names}")

if __name__ == "__main__":
    test_search_filter()
