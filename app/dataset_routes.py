from flask import Blueprint, current_app as app
from .datasets import list_datasets, register_dataset, view_dataset, upload_file, new_version, get_file, search_datasets, lineage_view

# Import data catalog routes from datasets.py to keep Flask clean
# This file exists to resolve the import in __init__.py
