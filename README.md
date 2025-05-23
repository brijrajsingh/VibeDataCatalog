# Data Catalog & Lineage Tool

A web application for managing datasets, tracking data lineage, and discovering relevant data assets within your organization.

## Features

- **Dataset Registration**: Create and maintain dataset metadata with tags and descriptions
- **File Management**: Upload CSV and Excel files to datasets with storage in Azure Blob Storage
- **File Preview**: View CSV and Excel files directly in the browser without downloading
- **Versioning**: Track dataset versions and changes over time
- **Lineage Tracking**: Visualize how datasets evolve and relate to each other
- **Search & Discovery**: Find relevant datasets through powerful search queries
- **User Management**: Authentication and activity tracking
- **Soft Delete**: Safely delete and restore datasets as needed

## Technology Stack

- **Frontend**: HTML, CSS, JavaScript with Bootstrap 5
- **Backend**: Python 3.9+ with Flask web framework
- **Database**: Azure Cosmos DB for metadata storage
- **Storage**: Azure Blob Storage for file storage
- **Authentication**: Custom user authentication with password hashing
- **Visualization**: D3.js for lineage visualization

## Setup Instructions

### Prerequisites

- Python 3.9+
- Azure Cosmos DB account
- Azure Blob Storage account

### Environment Configuration

1. Copy the `.env.example` file to `.env`:
   ```
   cp .env.example .env
   ```

2. Update the `.env` file with your Azure credentials:
   ```
   # Azure Settings
   COSMOSDB_ENDPOINT=your_cosmosdb_endpoint
   COSMOSDB_KEY=your_cosmosdb_key
   COSMOSDB_DATABASE=datacatalog
   COSMOSDB_CONTAINER=metadata

   # Azure Blob Storage
   AZURE_STORAGE_CONNECTION_STRING=your_storage_connection_string
   AZURE_BLOB_CONTAINER=datasets

   # Flask Settings
   SECRET_KEY=your_random_secret_key
   FLASK_ENV=development
   ```

### Installation

1. Create a virtual environment:
   ```
   python -m venv venv
   ```

2. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - Unix/MacOS: `source venv/bin/activate`

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

### Running the Application

1. Start the Flask development server:
   ```
   python run.py
   ```

2. Access the application at http://localhost:5000

### Docker Deployment

1. Build the Docker image:
   ```
   docker build -t datacatalog .
   ```

2. Run the Docker container:
   ```
   docker run -p 5000:5000 --env-file .env datacatalog
   ```

## Azure Setup

### Cosmos DB

1. Create a Cosmos DB account in Azure Portal
2. Create a database named `datacatalog`
3. Create a container named `metadata` with partition key `/type`

### Blob Storage

1. Create a Storage Account in Azure Portal
2. Create a Blob container named `datasets`
3. Get the connection string from Access Keys in the Storage Account settings

## Usage Guide

### Registering a Dataset

1. Click "Register Dataset" in the sidebar
2. Fill in dataset name, description, and tags
3. Submit the form to register the dataset metadata

### Uploading Files

1. Navigate to a dataset's detail page
2. Click "Upload File"
3. Select a CSV or Excel file from your computer
4. Submit to upload the file to Azure Blob Storage

### Creating New Versions

1. Navigate to a dataset's detail page
2. Click "New Version"
3. Update description and tags as needed
4. Submit to create a new version that inherits from the previous one

### Searching for Datasets

1. Use the search bar at the top of the page
2. Use advanced search syntax:
   - `tag:value` to search for specific tags
   - `by:username` to filter by creator
   - Combine terms like `sales tag:quarterly by:john`

### Viewing Dataset Lineage

1. Navigate to the Lineage view from the sidebar
2. Interact with the visualization:
   - Hover over nodes to see dataset details
   - Click nodes to navigate to datasets
   - Drag nodes to rearrange the visualization
   - Group datasets by family or view all relationships

## License

MIT License
