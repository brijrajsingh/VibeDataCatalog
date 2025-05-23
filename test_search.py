print("Testing tag search implementation...")
print("==================================")

# Sample datasets with different case tags
sample_datasets = [
    {
        "id": "1",
        "type": "dataset",
        "name": "Sales Data 2023",
        "description": "Monthly sales figures for 2023",
        "created_by": "john",
        "tags": ["Sales", "monthly", "2023"]
    },
    {
        "id": "2",
        "type": "dataset",
        "name": "Customer Analysis",
        "description": "Analysis of customer segments",
        "created_by": "sarah",
        "tags": ["customers", "ANALYSIS", "Marketing"]
    },
    {
        "id": "3",
        "type": "dataset",
        "name": "Product Inventory",
        "description": "Current inventory levels",
        "created_by": "mike",
        "tags": ["inventory", "products"]
    }
]

# Test cases with different tag capitalization
test_cases = [
    "tag:sales",         # Should match dataset 1 (with tag "Sales")
    "tag:ANALYSIS",      # Should match dataset 2 (with tag "ANALYSIS")
    "tag:marketing",     # Should match dataset 2 (with tag "Marketing")
    "tag:products",      # Should match dataset 3 (with tag "products")
    "tag:INVENTORY",     # Should match dataset 3 (with tag "inventory")
    "tag:nonexistent"    # Should match no datasets
]

# Test multiple tag filtering
multiple_tag_test_cases = [
    "tag:sales tag:monthly",     # Should match dataset 1 only
    "tag:ANALYSIS tag:marketing", # Should match dataset 2 only
    "tag:sales tag:inventory",    # Should match no datasets (no dataset has both)
]

print("\nSingle Tag Tests:")
print("=================")
# For each test case, filter the datasets based on the tag
for query in test_cases:
    tag_filter = query.split(':')[1].lower()
    
    filtered_datasets = []
    for dataset in sample_datasets:
        # Get all tags in lowercase for case-insensitive comparison
        dataset_tags = [tag.lower() for tag in dataset.get('tags', [])]
        
        # Check if the tag filter is present
        if tag_filter in dataset_tags:
            filtered_datasets.append(dataset)
    
    matched_names = [d["name"] for d in filtered_datasets]
    print(f"Query '{query}': Matched {len(filtered_datasets)} dataset(s): {matched_names}")

print("\nMultiple Tag Tests:")
print("==================")
# For multiple tag tests
for query in multiple_tag_test_cases:
    # Parse out all tags
    tag_parts = query.split()
    tag_filters = [part.split(':')[1].lower() for part in tag_parts]
    
    filtered_datasets = []
    for dataset in sample_datasets:
        dataset_tags = [tag.lower() for tag in dataset.get('tags', [])]
        
        # Check if ALL requested tags are present
        if all(tag_filter in dataset_tags for tag_filter in tag_filters):
            filtered_datasets.append(dataset)
    
    matched_names = [d["name"] for d in filtered_datasets]
    print(f"Query '{query}': Matched {len(filtered_datasets)} dataset(s): {matched_names}")

print("\nTest complete!")
