"""
Instructions for testing Excel file preview functionality in the Data Catalog

This document provides instructions on how to test the newly implemented Excel file preview feature:

1. Prerequisites:
   - Ensure that openpyxl and xlrd are installed: `pip install openpyxl xlrd`
   - Make sure your Azure Blob storage is properly configured

2. Steps to test Excel file preview:
   
   a) First, run the automated test to verify basic functionality:
      ```
      python test_excel_preview.py
      ```
      This will upload a test Excel file to your blob storage and attempt to preview it.
      
   b) Manual testing in the application:
      - Log in to the Data Catalog web application
      - Create a new dataset or select an existing one
      - Upload an Excel (.xlsx) file to the dataset
      - Go to the dataset view page
      - Click the "Preview" button next to the Excel file
      - Verify that the preview shows:
         * The first 10 rows of data in a table format
         * Column names as headers
         * Metadata showing the total number of rows and columns
      
   c) Edge cases to test:
      - Preview an Excel file with multiple sheets (it should show the first sheet)
      - Preview a very large Excel file (it should still only show the first 10 rows)
      - Preview an Excel file with formatting (it should show the data without formatting)
      - Preview both .xlsx (Excel 2007+) and .xls (older Excel format) files

3. Common issues and solutions:
   
   a) If you see an error about "unsupported format":
      - Make sure openpyxl is installed
      - Check that the file is actually a valid Excel file
   
   b) If you see missing data or incorrect formatting:
      - Try downloading the file directly to verify its contents
      - Excel files with complex formatting might not preview perfectly

4. Implementation details:
   
   The Excel preview feature is implemented in app/utils.py and uses pandas with the openpyxl engine
   to read Excel files. The preview shows the first 10 rows of the first sheet and extracts metadata
   like column count and names.
