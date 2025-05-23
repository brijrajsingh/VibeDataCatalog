# Testing the Soft Delete Functionality

This document provides instructions for manually testing the soft delete functionality in a running environment.

## 1. Setup

Ensure your application is running with the latest code deployed. You can use the following command:

```
python run.py
```

## 2. Testing Steps

### Basic Functionality

1. **Create Test Datasets**
   - Register at least 2 new datasets
   - Create at least 2 versions of one dataset
   - Add different tags and descriptions to help identify them

2. **Test Soft Delete**
   - Go to a dataset view page
   - Click the "Delete" button in the header actions
   - Verify the confirmation modal shows the correct dataset details
   - Confirm the deletion
   - Verify you're redirected appropriately
   - Check that the dataset no longer appears in the default list view

3. **Test Show/Hide Deleted Toggle**
   - Go to the datasets list page
   - Toggle "Show deleted datasets" to ON
   - Verify deleted datasets now appear with the "Deleted" badge
   - Verify the delete/restore action buttons are correct
   - Toggle back to OFF and verify deleted datasets are hidden

### Advanced Features

4. **Test Restore Functionality**
   - Show deleted datasets
   - Find a deleted dataset
   - Click the "Restore" button
   - Verify the dataset returns to normal state (no "Deleted" badge)
   - Verify it's visible when "Show deleted datasets" is OFF

5. **Test Search Filters**
   - Go to the search page
   - Try searching with `status:deleted` in the query
   - Verify only deleted datasets are shown
   - Try searching with `status:active` in the query
   - Verify only non-deleted datasets are shown
   - Try combining with other search terms (e.g., `tag:test status:deleted`)

6. **Test Lineage View**
   - Go to the lineage visualization page
   - Toggle "Show deleted datasets" to ON
   - Verify deleted datasets appear in red color with dashed borders
   - Hover over nodes to verify tooltip shows deletion status
   - Toggle back to OFF and verify deleted datasets are hidden

7. **Test Edge Cases**
   - Delete all versions of a dataset and verify behavior
   - Delete a dataset with child versions and check lineage display
   - Create a new version from a deleted dataset (should not be allowed)

## 3. Reporting Issues

If you find any issues during testing, please document them with:
- Steps to reproduce
- Expected behavior
- Actual behavior
- Screenshots if applicable

## 4. Clean-up

After testing, you can restore or permanently delete any test datasets you created.
