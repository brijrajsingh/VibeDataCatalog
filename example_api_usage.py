"""
Example script demonstrating how to use the Data Catalog API
"""

import requests
import json
import os
from pathlib import Path

# Configuration
API_KEY = "your-api-key-here"  # Replace with your actual API key
BASE_URL = "http://localhost:5000/api"  # Replace with your actual API URL
HEADERS = {"X-API-Key": API_KEY}

def create_dataset():
    """Create a new dataset"""
    print("Creating a new dataset...")
    
    dataset_data = {
        "name": "Sales Analytics Dataset",
        "description": "Comprehensive sales data for Q4 2023 analysis",
        "version": "1.0",
        "tags": ["sales", "analytics", "q4", "2023"],
        "metadata": {
            "department": "Sales",
            "quarter": "Q4 2023",
            "data_source": "CRM System"
        }
    }
    
    response = requests.post(
        f"{BASE_URL}/datasets",
        headers=HEADERS,
        json=dataset_data
    )
    
    if response.status_code == 201:
        result = response.json()
        print(f"✅ Dataset created successfully!")
        print(f"   Dataset ID: {result['dataset_id']}")
        return result['dataset_id']
    else:
        print(f"❌ Failed to create dataset: {response.text}")
        return None

def upload_file(dataset_id, file_path):
    """Upload a file to a dataset"""
    print(f"Uploading file {file_path} to dataset {dataset_id}...")
    
    if not os.path.exists(file_path):
        print(f"❌ File {file_path} does not exist")
        return None
    
    with open(file_path, 'rb') as file:
        files = {'file': file}
        data = {
            'description': f'Data file uploaded via API: {os.path.basename(file_path)}',
            'tags': 'api-upload,data'
        }
        
        response = requests.post(
            f"{BASE_URL}/datasets/{dataset_id}/files",
            headers=HEADERS,
            files=files,
            data=data
        )
    
    if response.status_code == 201:
        result = response.json()
        print(f"✅ File uploaded successfully!")
        print(f"   File ID: {result['file_id']}")
        print(f"   Filename: {result['filename']}")
        print(f"   Size: {result['size']} bytes")
        return result['file_id']
    else:
        print(f"❌ Failed to upload file: {response.text}")
        return None

def list_datasets():
    """List all datasets"""
    print("Fetching all datasets...")
    
    response = requests.get(f"{BASE_URL}/datasets", headers=HEADERS)
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Found {result['count']} datasets:")
        for dataset in result['datasets'][:5]:  # Show first 5
            print(f"   - {dataset['name']} (v{dataset['version']}) by {dataset['created_by']}")
        return result['datasets']
    else:
        print(f"❌ Failed to fetch datasets: {response.text}")
        return []

def search_datasets(query, tags=None):
    """Search datasets"""
    print(f"Searching for datasets with query: '{query}'")
    
    params = {'q': query}
    if tags:
        params['tags'] = ','.join(tags)
    
    response = requests.get(
        f"{BASE_URL}/datasets/search",
        headers=HEADERS,
        params=params
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Found {result['count']} matching datasets")
        for dataset in result['datasets']:
            print(f"   - {dataset['name']}: {dataset['description'][:100]}...")
        return result['datasets']
    else:
        print(f"❌ Failed to search datasets: {response.text}")
        return []

def list_files(dataset_id):
    """List files in a dataset"""
    print(f"Listing files in dataset {dataset_id}...")
    
    response = requests.get(
        f"{BASE_URL}/datasets/{dataset_id}/files",
        headers=HEADERS
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Dataset '{result['dataset_name']}' has {result['file_count']} files:")
        for file_info in result['files']:
            print(f"   - {file_info['filename']} ({file_info['size']} bytes)")
            print(f"     Uploaded by: {file_info['uploaded_by']} at {file_info['uploaded_at']}")
        return result['files']
    else:
        print(f"❌ Failed to list files: {response.text}")
        return []

def download_file(dataset_id, file_id, save_path):
    """Download a file from a dataset"""
    print(f"Getting download URL for file {file_id}...")
    
    # First, get the download URL
    response = requests.get(
        f"{BASE_URL}/datasets/{dataset_id}/files/{file_id}/download",
        headers=HEADERS
    )
    
    if response.status_code == 200:
        result = response.json()
        download_url = result['download_url']
        filename = result['filename']
        
        print(f"✅ Download URL obtained for {filename}")
        print(f"   Valid until: {result['expires_at']}")
        
        # Download the actual file
        file_response = requests.get(download_url)
        if file_response.status_code == 200:
            with open(save_path, 'wb') as f:
                f.write(file_response.content)
            print(f"✅ File downloaded to {save_path}")
            return True
        else:
            print(f"❌ Failed to download file: {file_response.text}")
            return False
    else:
        print(f"❌ Failed to get download URL: {response.text}")
        return False

def create_sample_csv_file():
    """Create a sample CSV file for testing"""
    sample_data = """name,age,city,salary
John Doe,30,New York,75000
Jane Smith,25,Los Angeles,65000
Bob Johnson,35,Chicago,80000
Alice Brown,28,Houston,70000
Charlie Wilson,32,Phoenix,72000"""
    
    filename = "sample_sales_data.csv"
    with open(filename, 'w') as f:
        f.write(sample_data)
    
    print(f"✅ Created sample file: {filename}")
    return filename

def create_new_version(parent_dataset_id):
    """Create a new version of an existing dataset"""
    print(f"Creating a new version of dataset {parent_dataset_id}...")
    
    # First, get the parent dataset to inherit properties
    response = requests.get(
        f"{BASE_URL}/datasets/{parent_dataset_id}",
        headers=HEADERS
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to get parent dataset: {response.text}")
        return None
    
    parent_dataset = response.json()['dataset']
    
    # Create new version with modified properties
    new_version_data = {
        "name": f"{parent_dataset['base_name']} v2.0",  # New version name
        "description": parent_dataset['description'] + " - Updated with additional analysis features",
        "version": "2.0",
        "tags": parent_dataset['tags'] + ["v2", "enhanced"],  # Add new tags
        "parent_id": parent_dataset_id,  # Link to parent
        "metadata": {
            "department": "Sales",
            "quarter": "Q1 2024",  # Updated metadata
            "data_source": "Enhanced CRM System",
            "improvements": ["Better data quality", "Additional metrics", "Performance optimizations"]
        }
    }
    
    response = requests.post(
        f"{BASE_URL}/datasets",
        headers=HEADERS,
        json=new_version_data
    )
    
    if response.status_code == 201:
        result = response.json()
        print(f"✅ New dataset version created successfully!")
        print(f"   New Dataset ID: {result['dataset_id']}")
        print(f"   Parent Dataset ID: {parent_dataset_id}")
        print(f"   Version: 2.0")
        return result['dataset_id']
    else:
        print(f"❌ Failed to create new version: {response.text}")
        return None

def get_dataset_lineage(dataset_id):
    """Get information about a dataset and its lineage"""
    print(f"Getting dataset lineage for {dataset_id}...")
    
    response = requests.get(
        f"{BASE_URL}/datasets/{dataset_id}",
        headers=HEADERS
    )
    
    if response.status_code == 200:
        dataset = response.json()['dataset']
        print(f"✅ Dataset: {dataset['name']}")
        print(f"   Base Name: {dataset['base_name']}")
        print(f"   Version: {dataset['version']}")
        print(f"   Created by: {dataset['created_by']}")
        
        if dataset.get('parent_id'):
            print(f"   Parent ID: {dataset['parent_id']}")
            print("   This is a derived version of another dataset")
        else:
            print("   This is the original dataset (no parent)")
            
        return dataset
    else:
        print(f"❌ Failed to get dataset: {response.text}")
        return None

def create_sample_csv_file_v2():
    """Create a sample CSV file for version 2 testing"""
    sample_data = """name,age,city,salary,department,performance_score
John Doe,30,New York,75000,Sales,8.5
Jane Smith,25,Los Angeles,65000,Marketing,9.2
Bob Johnson,35,Chicago,80000,Sales,7.8
Alice Brown,28,Houston,70000,HR,8.9
Charlie Wilson,32,Phoenix,72000,Sales,8.1
Diana Prince,29,Seattle,78000,Marketing,9.5
Edward Davis,33,Boston,82000,Sales,8.7
Fiona Green,26,Denver,68000,HR,8.3"""
    
    filename = "sample_sales_data_v2.csv"
    with open(filename, 'w') as f:
        f.write(sample_data)
    
    print(f"✅ Created enhanced sample file: {filename}")
    return filename

def main():
    """Main function demonstrating API usage"""
    print("🚀 Data Catalog API Usage Example")
    print("=" * 50)
    
    # Check if API key is set
    if API_KEY == "your-api-key-here":
        print("❌ Please set your API key in the script!")
        return
    
    try:
        # 1. List existing datasets
        datasets = list_datasets()
        print()
        
        # 2. Search for datasets
        search_results = search_datasets("sales", ["analytics"])
        print()
        
        # 3. Create a new dataset
        dataset_id = create_dataset()
        if not dataset_id:
            return
        print()
        
        # 4. Create and upload a sample file
        sample_file = create_sample_csv_file()
        file_id = upload_file(dataset_id, sample_file)
        if not file_id:
            return
        print()
        
        # 5. List files in the dataset
        files = list_files(dataset_id)
        print()
        
        # 6. Create a new version of the dataset
        new_version_id = create_new_version(dataset_id)
        if new_version_id:
            print()
            
            # 7. Get lineage information for the new version
            lineage_info = get_dataset_lineage(new_version_id)
            print()
            
            # 8. Upload a file to the new version
            sample_file_v2 = create_sample_csv_file_v2()
            file_id_v2 = upload_file(new_version_id, sample_file_v2)
            if file_id_v2:
                print()
                
                # 9. List files in the new version
                files_v2 = list_files(new_version_id)
                print()
        
        # 10. Download a file from the original dataset
        if files:
            download_path = "downloaded_" + sample_file
            success = download_file(dataset_id, file_id, download_path)
            print()
        
        # 11. Clean up sample files
        try:
            os.remove(sample_file)
            if 'sample_file_v2' in locals():
                os.remove(sample_file_v2)
            print(f"🧹 Cleaned up sample files")
        except:
            pass
        
        print("✅ API usage example completed successfully!")
        print(f"📊 Created original dataset: {dataset_id}")
        if 'new_version_id' in locals() and new_version_id:
            print(f"📊 Created new version: {new_version_id}")
        
    except Exception as e:
        print(f"❌ An error occurred: {str(e)}")

if __name__ == "__main__":
    main()
