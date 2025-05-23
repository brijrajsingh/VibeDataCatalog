"""
Test script to verify Excel file preview functionality
"""
import os
from azure.storage.blob import BlobServiceClient
import pandas as pd
import io
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Azure Configuration
AZURE_STORAGE_CONNECTION_STRING = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
AZURE_BLOB_CONTAINER = os.environ.get("AZURE_BLOB_CONTAINER")

def test_excel_preview():
    """Test that Excel files can be previewed correctly"""
    print("Testing Excel file preview functionality...")

    # Initialize Blob Storage client
    blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
    blob_container_client = blob_service_client.get_container_client(AZURE_BLOB_CONTAINER)

    # Create a simple Excel DataFrame for testing
    df = pd.DataFrame({
        'Name': ['John', 'Alice', 'Bob', 'Emily', 'David'],
        'Age': [30, 25, 35, 28, 42],
        'City': ['New York', 'Los Angeles', 'Chicago', 'Houston', 'Miami'],
        'Salary': [50000, 65000, 55000, 70000, 60000],
        'Department': ['HR', 'Engineering', 'Marketing', 'Engineering', 'Finance']
    })

    # Create BytesIO object to hold Excel file
    excel_buffer = io.BytesIO()
    
    # Write DataFrame to Excel file in memory
    df.to_excel(excel_buffer, index=False)
    excel_buffer.seek(0)  # Move to the beginning of the buffer

    # Upload to blob storage
    test_blob_name = "test/excel_preview_test.xlsx"
    print(f"Uploading test Excel file to {test_blob_name}...")
    
    blob_client = blob_service_client.get_blob_client(container=AZURE_BLOB_CONTAINER, blob=test_blob_name)
    blob_client.upload_blob(excel_buffer, overwrite=True)
      # Download and test preview function
    print("Testing preview functionality...")
    downloaded_blob = blob_client.download_blob().readall()
    
    try:
        # Try to read the Excel file with pandas using openpyxl engine
        test_df = pd.read_excel(io.BytesIO(downloaded_blob), engine='openpyxl')
        print("✓ Successfully read Excel file with pandas")
        print(f"✓ Found {len(test_df)} rows and {len(test_df.columns)} columns")
        print("✓ Columns:", list(test_df.columns))
        print("\nSample of the data:")
        print(test_df.head())
        
        # Now test the actual implementation from utils.py
        print("\nTesting the get_dataset_file_preview function...")
        
        # Import the function
        from app.utils import get_dataset_file_preview
        
        # Call the function with our test blob path
        preview_data = get_dataset_file_preview(test_blob_name)
        
        if preview_data['type'] == 'excel':
            print("✓ get_dataset_file_preview successfully recognized file as Excel")
            print(f"✓ Preview data contains {preview_data['column_info']['count']} columns")
            print(f"✓ Preview HTML successfully generated ({len(preview_data['preview'])} characters)")
            return True
        else:
            print(f"✗ get_dataset_file_preview failed to process Excel file correctly.")
            print(f"✗ Returned type: {preview_data['type']}")
            if 'error' in preview_data:
                print(f"✗ Error: {preview_data['error']}")
            return False
    except Exception as e:
        print(f"✗ Error reading Excel file: {str(e)}")
        print("\nThis might indicate missing dependencies or configuration issues.")
        print("Make sure openpyxl is installed: pip install openpyxl")
        return False

if __name__ == "__main__":
    test_excel_preview()
