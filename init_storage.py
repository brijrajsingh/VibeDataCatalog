"""
Initialize Azure Blob Storage container for the Data Catalog application.
This script will create the blob container if it doesn't exist.
"""

import os
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient, __version__
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Azure Blob Storage settings
AZURE_STORAGE_CONNECTION_STRING = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
AZURE_BLOB_CONTAINER = os.environ.get("AZURE_BLOB_CONTAINER", "datasets")

def main():
    """Initialize the blob container."""
    print(f"Azure Blob Storage SDK version: {__version__}")
    print(f"Connecting to Azure Blob Storage...")
    
    if not AZURE_STORAGE_CONNECTION_STRING:
        print("Error: Missing AZURE_STORAGE_CONNECTION_STRING in .env file")
        return
    
    try:
        # Create the BlobServiceClient object
        blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
        print(f"Connected to Blob Storage account: {blob_service_client.account_name}")
        
        # Check if the container exists and create if not
        container_client = blob_service_client.get_container_client(AZURE_BLOB_CONTAINER)
        try:
            container_properties = container_client.get_container_properties()
            print(f"Blob container '{AZURE_BLOB_CONTAINER}' already exists")
        except Exception:
            print(f"Creating blob container '{AZURE_BLOB_CONTAINER}'...")
            container_client = blob_service_client.create_container(AZURE_BLOB_CONTAINER)
            print(f"Blob container '{AZURE_BLOB_CONTAINER}' created successfully")
        
        print("Blob Storage initialization complete!")
    
    except Exception as ex:
        print(f"An error occurred: {ex}")

if __name__ == "__main__":
    main()
