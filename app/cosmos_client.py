import os
from azure.cosmos import CosmosClient

# Azure Configuration
ENDPOINT = os.environ.get("COSMOSDB_ENDPOINT")
KEY = os.environ.get("COSMOSDB_KEY")
DATABASE_NAME = os.environ.get("COSMOSDB_DATABASE")
USERS_CONTAINER_NAME = os.environ.get("COSMOSDB_USERS_CONTAINER")
METADATA_CONTAINER_NAME = os.environ.get("COSMOSDB_METADATA_CONTAINER")
ACTIVITIES_CONTAINER_NAME = os.environ.get("COSMOSDB_ACTIVITIES_CONTAINER")

# Initialize CosmosDB client
client = CosmosClient(ENDPOINT, credential=KEY)
database = client.get_database_client(DATABASE_NAME)

# Container clients
users_container = database.get_container_client(USERS_CONTAINER_NAME)
metadata_container = database.get_container_client(METADATA_CONTAINER_NAME)
activities_container = database.get_container_client(ACTIVITIES_CONTAINER_NAME)
