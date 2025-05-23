@datasets_bp.route('/search')
@login_required
def search_datasets():
    """Search for datasets based on name, tags, or uploaded by"""
    query_term = request.args.get('query', '').lower()
    show_deleted = request.args.get('show_deleted', '').lower() == 'true'
    
    if not query_term:
        return render_template('datasets/search.html', datasets=[], query='', show_deleted=show_deleted)
    
    # Parse the query for advanced search
    search_parts = query_term.split()
    tag_filters = []
    uploader_filters = []
    name_filters = []
    status_filter = None  # 'active', 'deleted', or None
    
    for part in search_parts:
        if part.startswith('tag:'):
            tag_filters.append(part[4:].lower())  # Store lowercase version of tag
        elif part.startswith('by:'):
            uploader_filters.append(part[3:].lower())  # Store lowercase version of uploader
        elif part == 'status:deleted':
            status_filter = 'deleted'
        elif part == 'status:active':
            status_filter = 'active'
        else:
            name_filters.append(part)
    
    # Construct the CosmosDB query
    filters = []
    
    # Handle deleted status
    if status_filter == 'deleted':
        filters.append("IS_DEFINED(c.is_deleted)")
    elif status_filter == 'active':
        filters.append("NOT IS_DEFINED(c.is_deleted)")
    elif not show_deleted:  # Default behavior is to hide deleted unless explicitly requested
        filters.append("NOT IS_DEFINED(c.is_deleted)")
    
    if name_filters:
        name_query = ' OR '.join([f"CONTAINS(LOWER(c.name), '{name.lower()}')" for name in name_filters])
        desc_query = ' OR '.join([f"CONTAINS(LOWER(c.description), '{name.lower()}')" for name in name_filters])
        filters.append(f"({name_query} OR {desc_query})")
    
    if uploader_filters:
        uploader_conditions = []
        for uploader in uploader_filters:
            uploader_conditions.append(f"LOWER(c.created_by) = '{uploader.lower()}'")
        filters.append(f"({' OR '.join(uploader_conditions)})")
    
    # For tag filters, we'll fetch all datasets with any tags and filter afterward
    # We can't do case-insensitive array matching in CosmosDB SQL
    has_tag_filter = bool(tag_filters)
    if has_tag_filter:
        # Just check that tags array exists and is not empty
        filters.append("(ARRAY_LENGTH(c.tags) > 0)")
    
    # Combine filters
    main_query = "SELECT * FROM c WHERE c.type = 'dataset'"
    if filters:
        main_query += " AND " + " AND ".join(filters)
        
    # Execute query
    all_datasets = list(container.query_items(query=main_query, enable_cross_partition_query=True))
    
    # Post-query filtering for tags (case-insensitive)
    if has_tag_filter:
        filtered_datasets = []
        for dataset in all_datasets:
            # Get all tags in lowercase for case-insensitive comparison
            dataset_tags = [tag.lower() for tag in dataset.get('tags', [])]
            
            # Check if all requested tags are present
            if all(tag_filter in dataset_tags for tag_filter in tag_filters):
                filtered_datasets.append(dataset)
                
        datasets = filtered_datasets
    else:
        datasets = all_datasets
    
    return render_template('datasets/search.html', datasets=datasets, query=query_term, show_deleted=show_deleted)
