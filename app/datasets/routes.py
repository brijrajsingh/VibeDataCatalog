from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from .models import DatasetModel
from .files import FileManager
from .search import DatasetSearch
from .utils import convert_to_local_time, group_datasets_by_base_name, log_user_activity

# Blueprint for dataset routes
datasets_bp = Blueprint('datasets', __name__, url_prefix='/datasets')

@datasets_bp.route('/')
@login_required
def list_datasets():
    """List all datasets"""
    show_deleted = request.args.get('show_deleted', '').lower() == 'true'
    browser_timezone = request.args.get('timezone', 'Asia/Calcutta')
    
    datasets = DatasetModel.list_all(show_deleted)
    convert_to_local_time(datasets, browser_timezone)
    dataset_groups = group_datasets_by_base_name(datasets)
    
    return render_template('datasets/list.html', dataset_groups=dataset_groups, show_deleted=show_deleted)

@datasets_bp.route('/register', methods=['GET', 'POST'])
@login_required
def register_dataset():
    """Register a new dataset"""
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        tags = [tag.strip() for tag in request.form.get('tags', '').split(',') if tag.strip()]
        
        try:
            dataset_id, dataset = DatasetModel.create(
                name=name,
                description=description,
                tags=tags,
                created_by=current_user.username
            )
            log_user_activity(current_user.username, 'dataset_created', f"Created dataset '{name}'", dataset_id)
            flash('Dataset registered successfully', 'success')
            return redirect(url_for('datasets.view_dataset', dataset_id=dataset_id))
        except ValueError as e:
            flash(str(e), 'error')
            return redirect(request.url)
    
    return render_template('datasets/register.html')

@datasets_bp.route('/<dataset_id>')
@login_required
def view_dataset(dataset_id):
    """View a specific dataset"""
    browser_timezone = request.args.get('timezone', 'UTC')
    
    dataset = DatasetModel.get_by_id(dataset_id)
    if not dataset:
        flash('Dataset not found', 'error')
        return redirect(url_for('datasets.list_datasets'))
    
    convert_to_local_time([dataset], browser_timezone)
    versions = DatasetModel.get_versions(dataset['base_name'])
    lineage = DatasetModel.get_lineage(dataset)
    
    return render_template('datasets/view.html', dataset=dataset, versions=versions, lineage=lineage)

@datasets_bp.route('/<dataset_id>/upload', methods=['GET', 'POST'])
@login_required
def upload_file(dataset_id):
    """Upload a file to a dataset"""
    dataset = DatasetModel.get_by_id(dataset_id)
    if not dataset:
        flash('Dataset not found', 'error')
        return redirect(url_for('datasets.list_datasets'))
    
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        description = request.form.get('description', '')
        tags = [tag.strip() for tag in request.form.get('tags', '').split(',') if tag.strip()]
        
        try:
            file_id, file_info = FileManager.upload_to_dataset(
                dataset_id, file, current_user.username, description, tags
            )
            log_user_activity(
                current_user.username, 'file_uploaded',
                f"Uploaded file '{file.filename}' to dataset '{dataset['name']}'",
                dataset_id, file_id
            )
            flash('File uploaded successfully', 'success')
            return redirect(url_for('datasets.view_dataset', dataset_id=dataset_id))
        except ValueError as e:
            flash(str(e), 'error')
            return redirect(request.url)
    
    return render_template('datasets/upload.html', dataset=dataset)

@datasets_bp.route('/<dataset_id>/new_version', methods=['GET', 'POST'])
@login_required
def new_version(dataset_id):
    """Create a new version of a dataset"""
    parent_dataset = DatasetModel.get_by_id(dataset_id)
    if not parent_dataset:
        flash('Dataset not found', 'error')
        return redirect(url_for('datasets.list_datasets'))
    
    if request.method == 'POST':
        description = request.form.get('description', parent_dataset['description'])
        tags = [tag.strip() for tag in request.form.get('tags', ','.join(parent_dataset['tags'])).split(',') if tag.strip()]
        
        try:
            new_dataset_id, new_dataset = DatasetModel.create(
                name="temp_name",
                description=description,
                tags=tags,
                created_by=current_user.username,
                parent_id=parent_dataset['id'],
                base_name=parent_dataset['base_name']
            )
            
            # Update name with version number
            new_dataset['name'] = f"{parent_dataset['base_name']} v{new_dataset['version']}"
            DatasetModel.update(new_dataset)
            
            log_user_activity(
                current_user.username, 'dataset_version_created',
                f"Created version {new_dataset['version']} of dataset '{parent_dataset['base_name']}'",
                new_dataset_id
            )
            flash(f'New dataset version {new_dataset["version"]} created', 'success')
            return redirect(url_for('datasets.view_dataset', dataset_id=new_dataset_id))
        except ValueError as e:
            flash(str(e), 'error')
            return redirect(request.url)
    
    return render_template('datasets/new_version.html', dataset=parent_dataset)

@datasets_bp.route('/search')
@login_required
def search_datasets():
    """Search for datasets"""
    query_term = request.args.get('query', '')
    show_deleted = request.args.get('show_deleted', '').lower() == 'true'
    
    datasets = DatasetSearch.search(query_term, show_deleted)
    convert_to_local_time(datasets, 'Asia/Calcutta')
    
    return render_template('datasets/search.html', datasets=datasets, query=query_term, show_deleted=show_deleted)

@datasets_bp.route('/lineage')
@login_required
def lineage_view():
    """View the lineage graph of all datasets"""
    show_deleted = request.args.get('show_deleted', '').lower() == 'true'
    nodes, links = DatasetSearch.get_lineage_data(show_deleted)
    
    return render_template('datasets/lineage.html', nodes=nodes, links=links, show_deleted=show_deleted)

@datasets_bp.route('/<dataset_id>/file/<file_id>')
@login_required
def get_file(dataset_id, file_id):
    """Get a file from a dataset with a SAS URL for access"""
    dataset, file_info = FileManager.get_from_dataset(dataset_id, file_id)
    
    if not dataset:
        flash('Dataset not found', 'error')
        return redirect(url_for('datasets.list_datasets'))
    
    if not file_info:
        flash('File not found', 'error')
        return redirect(url_for('datasets.view_dataset', dataset_id=dataset_id))
    
    # Generate SAS URL for download
    from ..utils import generate_blob_sas_url
    blob_url = generate_blob_sas_url(file_info['blob_path'], hours_valid=1)
    
    # Log download activity
    log_user_activity(
        current_user.username, 'file_download',
        f"Downloaded file '{file_info['filename']}' from dataset '{dataset['name']}'",
        dataset_id, file_id
    )
    
    return redirect(blob_url)

@datasets_bp.route('/<dataset_id>/file/<file_id>/direct-link')
@login_required
def get_file_direct_link(dataset_id, file_id):
    """Get a direct link to a file with a 5-hour SAS token"""
    dataset, file_info = FileManager.get_from_dataset(dataset_id, file_id)
    
    if not dataset:
        flash('Dataset not found', 'error')
        return redirect(url_for('datasets.list_datasets'))
    
    if not file_info:
        flash('File not found', 'error')
        return redirect(url_for('datasets.view_dataset', dataset_id=dataset_id))
    
    # Generate SAS URL for 5 hours
    from ..utils import generate_blob_sas_url
    blob_url = generate_blob_sas_url(file_info['blob_path'], hours_valid=5)
    
    # Log this activity
    log_user_activity(
        current_user.username, 'file_view',
        f"Viewed file '{file_info['filename']}' from dataset '{dataset['name']}'",
        dataset_id, file_id
    )
    
    return redirect(blob_url)

@datasets_bp.route('/<dataset_id>/file/<file_id>/preview')
@login_required
def preview_file(dataset_id, file_id):
    """Preview the contents of a file from a dataset"""
    browser_timezone = request.args.get('timezone', 'UTC')
    
    dataset, file_info = FileManager.get_from_dataset(dataset_id, file_id)
    
    if not dataset:
        flash('Dataset not found', 'error')
        return redirect(url_for('datasets.list_datasets'))
    
    if not file_info:
        flash('File not found', 'error')
        return redirect(url_for('datasets.view_dataset', dataset_id=dataset_id))
    
    # Convert file timestamp
    convert_to_local_time([{'files': [file_info]}], browser_timezone)
    
    # Get file preview
    from ..utils import get_dataset_file_preview
    preview_data = get_dataset_file_preview(file_info['blob_path'])
    
    # Add file metadata
    preview_data['file_info'] = {
        'filename': file_info['filename'],
        'uploaded_by': file_info['uploaded_by'],
        'uploaded_at': file_info.get('uploaded_at_local', file_info['uploaded_at']),
        'size_bytes': file_info['size_bytes']
    }
    
    return render_template('datasets/preview.html', 
                           dataset=dataset, 
                           file=file_info, 
                           preview_data=preview_data)

@datasets_bp.route('/<dataset_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_dataset(dataset_id):
    """Edit dataset metadata (tags and description)"""
    dataset = DatasetModel.get_by_id(dataset_id)
    if not dataset:
        flash('Dataset not found', 'error')
        return redirect(url_for('datasets.list_datasets'))
    
    # Check permissions
    if dataset['created_by'] != current_user.username:
        flash('You can only edit datasets you created', 'error')
        return redirect(url_for('datasets.view_dataset', dataset_id=dataset_id))
    
    if dataset.get('is_deleted', False):
        flash('Cannot edit deleted datasets', 'error')
        return redirect(url_for('datasets.view_dataset', dataset_id=dataset_id))
    
    if request.method == 'POST':
        new_description = request.form.get('description', '').strip()
        new_tags = [tag.strip() for tag in request.form.get('tags', '').split(',') if tag.strip()]
        
        if not new_description:
            flash('Description cannot be empty', 'error')
            return redirect(request.url)
        
        # Track changes
        changes = []
        if dataset['description'] != new_description:
            changes.append('description')
        if set(dataset.get('tags', [])) != set(new_tags):
            changes.append('tags')
        
        if not changes:
            flash('No changes made', 'info')
            return redirect(url_for('datasets.view_dataset', dataset_id=dataset_id))
        
        # Update dataset
        dataset['description'] = new_description
        dataset['tags'] = new_tags
        dataset['updated_at'] = datetime.utcnow().isoformat()
        dataset['updated_by'] = current_user.username
        
        try:
            DatasetModel.update(dataset)
            
            change_description = ', '.join(changes)
            log_user_activity(
                current_user.username, 'dataset_metadata_updated',
                f"Updated {change_description} for dataset '{dataset['name']}'",
                dataset_id
            )
            
            flash(f'Dataset metadata updated successfully ({change_description})', 'success')
            return redirect(url_for('datasets.view_dataset', dataset_id=dataset_id))
            
        except Exception as e:
            flash(f'Failed to update dataset: {str(e)}', 'error')
            return redirect(request.url)
    
    return render_template('datasets/edit.html', dataset=dataset)

@datasets_bp.route('/<dataset_id>/delete', methods=['POST'])
@login_required
def soft_delete_dataset(dataset_id):
    """Soft delete a dataset version"""
    try:
        dataset = DatasetModel.soft_delete(dataset_id, current_user.username)
        log_user_activity(
            current_user.username, 'dataset_delete',
            f"Soft deleted dataset '{dataset['name']}' (version {dataset['version']})",
            dataset_id
        )
        flash(f"Dataset '{dataset['name']}' version {dataset['version']} has been deleted", 'success')
        
        # Redirect to latest available version or dataset list
        versions = DatasetModel.get_versions(dataset['base_name'])
        active_versions = [v for v in versions if not v.get('is_deleted')]
        
        if active_versions:
            return redirect(url_for('datasets.view_dataset', dataset_id=active_versions[0]['id']))
        
        return redirect(url_for('datasets.list_datasets'))
        
    except ValueError as e:
        flash(str(e), 'error')
        return redirect(url_for('datasets.list_datasets'))

@datasets_bp.route('/<dataset_id>/restore', methods=['POST'])
@login_required
def restore_dataset(dataset_id):
    """Restore a soft-deleted dataset version"""
    try:
        dataset = DatasetModel.restore(dataset_id)
        log_user_activity(
            current_user.username, 'dataset_restore',
            f"Restored dataset '{dataset['name']}' (version {dataset['version']})",
            dataset_id
        )
        flash(f"Dataset '{dataset['name']}' version {dataset['version']} has been restored", 'success')
        return redirect(url_for('datasets.view_dataset', dataset_id=dataset_id))
    except ValueError as e:
        flash(str(e), 'error')
        return redirect(url_for('datasets.list_datasets'))

@datasets_bp.route('/<dataset_id>/set_production', methods=['POST'])
@login_required
def set_production_status(dataset_id):
    """Set a dataset version as production or remove production status"""
    action = request.form.get('action')  # 'set' or 'unset'
    is_production = action == 'set'
    
    try:
        dataset = DatasetModel.set_production(dataset_id, is_production, current_user.username)
        
        activity_type = 'dataset_production_set' if is_production else 'dataset_production_unset'
        message = f"{'Set' if is_production else 'Removed'} production status {'for' if is_production else 'from'} dataset '{dataset['name']}' (version {dataset['version']})"
        
        log_user_activity(current_user.username, activity_type, message, dataset_id)
        
        status_text = 'set as production' if is_production else 'removed from production'
        flash(f"Dataset '{dataset['name']}' version {dataset['version']} has been {status_text}", 'success')
        
        return redirect(url_for('datasets.view_dataset', dataset_id=dataset_id))
        
    except ValueError as e:
        flash(str(e), 'error')
        return redirect(url_for('datasets.view_dataset', dataset_id=dataset_id))

# Only keep this one API endpoint for tags autocomplete - move the rest to api_routes.py
@datasets_bp.route('/api/tags')
@login_required
def get_all_tags():
    """Get all unique tags used in datasets for autocomplete"""
    tags = DatasetModel.get_all_tags()
    return jsonify(tags)
