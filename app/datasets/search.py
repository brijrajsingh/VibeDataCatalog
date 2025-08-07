from ..cosmos_client import metadata_container

class DatasetSearch:
    """Handle dataset search operations"""
    
    @staticmethod
    def search(query_term='', show_deleted=False):
        """Search datasets with advanced filtering"""
        if not query_term:
            return []
        
        # Parse search query
        search_parts = query_term.split()
        tag_filters = []
        uploader_filters = []
        name_filters = []
        status_filter = None
        
        for part in search_parts:
            if part.startswith('tag:'):
                tag_filters.append(part[4:].lower())
            elif part.startswith('by:'):
                uploader_filters.append(part[3:].lower())
            elif part == 'status:deleted':
                status_filter = 'deleted'
            elif part == 'status:active':
                status_filter = 'active'
            elif part == 'status:production':
                status_filter = 'production'
            else:
                name_filters.append(part)
        
        # Build CosmosDB query
        filters = []
        
        # Status filtering
        if status_filter == 'deleted':
            filters.append("IS_DEFINED(c.is_deleted)")
        elif status_filter == 'production':
            filters.append("NOT IS_DEFINED(c.is_deleted) AND c.is_production = true")
        elif status_filter == 'active':
            filters.append("NOT IS_DEFINED(c.is_deleted) AND (NOT IS_DEFINED(c.is_production) OR c.is_production = false)")
        elif not show_deleted:
            filters.append("NOT IS_DEFINED(c.is_deleted)")
        
        # Name/description filtering
        if name_filters:
            name_query = ' OR '.join([f"CONTAINS(LOWER(c.name), '{name.lower()}')" for name in name_filters])
            desc_query = ' OR '.join([f"CONTAINS(LOWER(c.description), '{name.lower()}')" for name in name_filters])
            filters.append(f"({name_query} OR {desc_query})")
        
        # Uploader filtering
        if uploader_filters:
            uploader_conditions = []
            for uploader in uploader_filters:
                uploader_conditions.append(f"LOWER(c.created_by) = '{uploader.lower()}'")
            filters.append(f"({' OR '.join(uploader_conditions)})")
        
        # Tag filtering (pre-filter for datasets with tags)
        has_tag_filter = bool(tag_filters)
        if has_tag_filter:
            filters.append("(ARRAY_LENGTH(c.tags) > 0)")
        
        # Execute query
        main_query = "SELECT * FROM c"
        if filters:
            main_query += " WHERE " + " AND ".join(filters)
        
        all_datasets = list(metadata_container.query_items(query=main_query, enable_cross_partition_query=True))
        
        # Post-process tag filtering
        if has_tag_filter:
            filtered_datasets = []
            for dataset in all_datasets:
                dataset_tags = []
                if 'tags' in dataset and dataset['tags']:
                    dataset_tags = [tag.lower() for tag in dataset['tags']]
                
                if all(tag_filter in dataset_tags for tag_filter in tag_filters):
                    filtered_datasets.append(dataset)
            
            return filtered_datasets
        
        return all_datasets
    
    @staticmethod
    def get_lineage_data(show_deleted=False):
        """Get data for lineage visualization"""
        if show_deleted:
            query = "SELECT c.id, c.name, c.version, c.base_name, c.parent_id, c.tags, c.is_deleted FROM c"
        else:
            query = "SELECT c.id, c.name, c.version, c.base_name, c.parent_id, c.tags FROM c WHERE NOT IS_DEFINED(c.is_deleted)"
        
        datasets = list(metadata_container.query_items(query=query, enable_cross_partition_query=True))
        
        # Format data for visualization
        nodes = []
        links = []
        
        for dataset in datasets:
            node_data = {
                'id': dataset['id'],
                'name': dataset['name'],
                'version': dataset['version'],
                'base_name': dataset['base_name'],
                'tags': dataset.get('tags', [])
            }
            
            if dataset.get('is_deleted'):
                node_data['is_deleted'] = True
            
            nodes.append(node_data)
            
            # Create links between versions
            if dataset.get('parent_id'):
                links.append({
                    'source': dataset['parent_id'],
                    'target': dataset['id']
                })
        
        return nodes, links
