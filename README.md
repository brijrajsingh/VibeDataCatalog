# Vibe Data Catalog

A comprehensive data catalog and lineage tracking system built with Flask and Azure services.

## Features

- Dataset registration and versioning
- File upload and management with Azure Blob Storage
- Data lineage tracking and visualization
- Tag-based categorization and search
- User authentication and authorization
- API access for programmatic interaction

## Prerequisites

- Python 3.10 or higher
- Azure Cosmos DB account
- Azure Blob Storage account
- uv (Python package manager)

## Installation

### Install uv

```bash
# On macOS and Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# On Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or using pip
pip install uv
```

### Setup Project

1. Clone the repository:
```bash
git clone <repository-url>
cd VibeDataCatalog
```

2. Create environment file:
```bash
cp .env.template .env
# Edit .env with your Azure credentials and configuration
```

3. Create virtual environment and install dependencies using uv:
```bash
# Create virtual environment
uv venv

# Activate virtual environment
# On macOS/Linux:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate

# Install dependencies
uv pip install -e .

# Or install with dev dependencies
uv pip install -e ".[dev]"
```

4. Initialize the database:
```bash
python init_db.py
```

5. Run the application:
```bash
flask run
# Or
python run.py
```

## Development

### Using uv for package management

```bash
# Add a new dependency
uv pip install package-name
uv pip freeze > requirements.txt

# Install from requirements.txt
uv pip install -r requirements.txt

# Upgrade packages
uv pip install --upgrade package-name

# Install in editable mode for development
uv pip install -e .
```

### Running tests

```bash
pytest
# With coverage
pytest --cov=app
```

### Code formatting

```bash
black app/
flake8 app/
```

## API Usage

The application provides REST API endpoints for programmatic access. See the user profile page after login for API key and usage examples.

## Environment Variables

See `.env.template` for all available configuration options.

## License

[Your License Here]
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
