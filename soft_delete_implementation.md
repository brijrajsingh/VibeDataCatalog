# Dataset Soft Delete Implementation

This feature adds the ability to soft delete dataset versions instead of permanently removing them.

## Features

1. Soft delete a dataset version
2. Restore a previously deleted dataset version
3. Toggle visibility of deleted datasets in list view and search
4. Special visual indicators for deleted datasets
5. Additional search filter: `status:deleted` and `status:active`

## Implementation Details

All of the necessary changes have been implemented and tested. The following updates were made:

1. Templates updated:
   - `app/templates/datasets/view.html` - Added delete button, delete confirmation modal, and restore button for deleted datasets
   - `app/templates/datasets/list.html` - Added toggle to show/hide deleted datasets and visual indicators
   - `app/templates/datasets/search.html` - Added toggle to show/hide deleted datasets and visual indicators

2. Backend functions added to `app/datasets.py`:
   - `soft_delete_dataset` - Marks a dataset as deleted by adding the is_deleted flag
   - `restore_dataset` - Removes the deletion flags from a dataset

3. Updates to existing functions:
   - `list_datasets` - Added show_deleted parameter and filtering
   - `search_datasets` - Added show_deleted parameter and status filter options
   - `view_dataset` - Added handling for deleted dataset display

4. Testing:
   - `test_soft_delete.py` - Script for testing the soft delete functionality

## How It Works

### Database Schema Changes

- Adds `is_deleted` field (boolean) to dataset record when deleted
- Adds `deleted_by` field (string) to track who deleted it
- Adds `deleted_at` field (ISO timestamp) to track when it was deleted

### Visual Indicators

- Deleted dataset versions are displayed with a red "Deleted" badge in all views
- In the lineage visualization, deleted datasets are displayed in red color with a dashed border
- List views include a toggle to show/hide deleted datasets

### Soft Delete Process

1. User clicks the "Delete" button on a dataset version page
2. Confirmation modal appears showing dataset details
3. On confirmation, dataset is flagged as deleted but not removed from database
4. User is redirected to:
   - The latest non-deleted version if available
   - The datasets list if no active versions remain

### Restore Process

1. User views a deleted dataset (visible with the "Show deleted datasets" toggle)
2. User clicks the "Restore" button
3. Dataset's deletion flags are removed
4. Dataset returns to normal visible state

## Security Considerations

- Both delete and restore operations require authentication
- Activity tracking records both deletion and restoration events

## Testing Recommendations

1. Create a dataset with multiple versions
2. Delete one version and verify it's hidden by default
3. Toggle "Show deleted datasets" and verify it appears
4. Verify delete indicators appear correctly
5. Restore the dataset and verify it returns to normal
6. Test search filtering with `status:deleted` and `status:active`
