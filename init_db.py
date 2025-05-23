"""
Initialize Azure Cosmos DB database and container for the Data Catalog application.
This script will:
1. Create the database if it doesn't exist
2. Create the container if it doesn't exist
3. Create a sample user for testing
"""

import os
from azure.cosmos import CosmosClient, exceptions
from dotenv import load_dotenv
import uuid
from werkzeug.security import generate_password_hash

# Load environment variables
load_dotenv()

# Azure Cosmos DB settings
ENDPOINT = os.environ.get("COSMOSDB_ENDPOINT")
KEY = os.environ.get("COSMOSDB_KEY")
DATABASE_NAME = os.environ.get("COSMOSDB_DATABASE", "datacatalog")
CONTAINER_NAME = os.environ.get("COSMOSDB_CONTAINER", "metadata")

def main():
    """Initialize the database and container."""
    print(f"Connecting to Azure Cosmos DB at {ENDPOINT}...")
    
    if not ENDPOINT or not KEY:
        print("Error: Missing COSMOSDB_ENDPOINT or COSMOSDB_KEY in .env file")
        return
    
    # Initialize the Cosmos client
    client = CosmosClient(ENDPOINT, credential=KEY)
    
    # Create database if it doesn't exist
    try:
        database = client.create_database_if_not_exists(id=DATABASE_NAME)
        print(f"Database '{DATABASE_NAME}' exists or created successfully")
    except exceptions.CosmosResourceExistsError:
        print(f"Database '{DATABASE_NAME}' already exists")
        database = client.get_database_client(DATABASE_NAME)
    
    # Create container if it doesn't exist
    try:
        container = database.create_container_if_not_exists(
            id=CONTAINER_NAME, 
            partition_key="/type",
            offer_throughput=400
        )
        print(f"Container '{CONTAINER_NAME}' exists or created successfully")
    except exceptions.CosmosResourceExistsError:
        print(f"Container '{CONTAINER_NAME}' already exists")
        container = database.get_container_client(CONTAINER_NAME)
    
    # Create a test user if no users exist
    query = "SELECT * FROM c WHERE c.type = 'user'"
    users = list(container.query_items(query=query, enable_cross_partition_query=True))
    
    if not users:
        print("No users found. Creating a test user...")
        user_id = str(uuid.uuid4())
        test_user = {
            'id': user_id,
            'type': 'user',
            'username': 'testuser',
            'email': 'test@example.com',
            'password': generate_password_hash('password')
        }
        
        container.create_item(body=test_user)
        print(f"Test user created with username 'testuser' and password 'password'")
    else:
        print(f"Found {len(users)} existing users. Skipping test user creation.")
    
    print("Database initialization complete!")

if __name__ == "__main__":
    main()
