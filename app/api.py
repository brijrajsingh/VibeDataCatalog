from flask import jsonify
from . import app
from .auth import login_required
from .services import cosmos_service

@app.route('/api/dataset/<dataset_id>/lineage')
@login_required
def get_dataset_lineage(dataset_id):
    """Get lineage information for a specific dataset and its immediate relationships"""
    try:
        # Get the target dataset
        target_dataset = cosmos_service.get_dataset(dataset_id)
        if not target_dataset:
            return jsonify({'error': 'Dataset not found'}), 404
        
        nodes = []
        edges = []
        visited = set()
        
        def add_dataset_and_relatives(dataset, depth=0, max_depth=2):
            """Add dataset and its immediate relatives to the graph"""
            if not dataset or dataset['id'] in visited or depth > max_depth:
                return
            
            visited.add(dataset['id'])
            
            # Add node
            nodes.append({
                'id': dataset['id'],
                'name': dataset['name'],
                'version': dataset.get('version', 1),
                'description': dataset.get('description', ''),
                'parent_id': dataset.get('parent_id'),
                'created_at': dataset.get('created_at', '')
            })
            
            # Add parent relationship
            if dataset.get('parent_id'):
                parent = cosmos_service.get_dataset(dataset['parent_id'])
                if parent:
                    edges.append({
                        'source': dataset['parent_id'],
                        'target': dataset['id']
                    })
                    add_dataset_and_relatives(parent, depth + 1, max_depth)
            
            # Add children relationships
            children = cosmos_service.get_dataset_children(dataset['id'])
            for child in children[:5]:  # Limit to 5 children for clarity
                edges.append({
                    'source': dataset['id'],
                    'target': child['id']
                })
                add_dataset_and_relatives(child, depth + 1, max_depth)
        
        # Start with the target dataset
        add_dataset_and_relatives(target_dataset)
        
        return jsonify({
            'nodes': nodes,
            'edges': edges
        })
        
    except Exception as e:
        print(f"Error getting dataset lineage: {e}")
        return jsonify({'error': 'Failed to load lineage data'}), 500