# Excel File Preview in Data Catalog

This document explains how Excel (.xlsx and .xls) files are previewed in the Data Catalog application.

## Overview

The Data Catalog now supports previewing Excel files directly in the web interface, similar to how CSV files are previewed. This allows users to quickly examine the contents of Excel files without downloading them first.

## Features

- **Preview the first 10 rows** of Excel spreadsheets
- **Display column headers** to understand data structure
- **Show metadata** including row count, column count, and column names
- **Support for both .xlsx and .xls** file formats
- **Handle large files** efficiently by only loading a small preview

## Implementation Details

### Backend

The Excel preview functionality is implemented in `app/utils.py` within the `get_dataset_file_preview` function. It uses:

- **pandas**: For reading and processing Excel files
- **openpyxl**: As the engine for reading modern Excel (.xlsx) files
- **xlrd**: For handling older Excel (.xls) files

The implementation:
1. Fetches the file content from Azure Blob Storage
2. Uses pandas to read the Excel file with the appropriate engine
3. Extracts metadata (row count, column count, column names)
4. Generates HTML for the first 10 rows
5. Returns the preview data in a structured format

### Frontend

The preview is displayed using the `datasets/preview.html` template, which:
- Shows file metadata in a sidebar
- Displays the first 10 rows in a formatted table
- Provides information about the total number of rows and columns
- Shows the column headers as badges

## Limitations

- Only the **first sheet** of multi-sheet Excel files is previewed
- **Complex formatting** (colors, merges, etc.) is not preserved
- **Formulas** are shown as their calculated values, not the actual formulas
- Very **large Excel files** might take longer to generate previews

## Testing

You can test the Excel preview functionality using:
1. The `test_excel_preview.py` script, which verifies the functionality works
2. The `generate_excel_samples.py` script, which creates various test Excel files
3. Manual upload and preview of Excel files in the web interface

## Troubleshooting

If Excel previews aren't working correctly:

1. **Check dependencies** are installed:
   ```
   pip install pandas openpyxl xlrd
   ```

2. **Verify the Excel file is valid** by opening it in Excel or another application

3. **Check for errors** in the application logs

4. **Try with a simple Excel file** first to isolate any issues

## User Instructions

Users can preview Excel files by:
1. Navigate to a dataset that contains Excel files
2. Click the "Preview" button next to any Excel file
3. View the first 10 rows and file metadata in the preview page

The preview page also provides options to download the file or view it directly in the browser with a temporary link.
