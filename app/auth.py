from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import json
import os
from azure.cosmos import CosmosClient

# Configuration for Azure Cosmos DB
ENDPOINT = os.environ.get("COSMOSDB_ENDPOINT")
KEY = os.environ.get("COSMOSDB_KEY")
DATABASE_NAME = os.environ.get("COSMOSDB_DATABASE")
CONTAINER_NAME = os.environ.get("COSMOSDB_CONTAINER")

# Initialize CosmosDB client
client = CosmosClient(ENDPOINT, credential=KEY)
database = client.get_database_client(DATABASE_NAME)
container = database.get_container_client(CONTAINER_NAME)

# Initialize login manager
login_manager = LoginManager()
login_manager.login_view = 'auth.login'

# Blueprint for authentication routes
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

class User(UserMixin):
    def __init__(self, id, username, email, password):
        self.id = id
        self.username = username
        self.email = email
        self.password = password

@login_manager.user_loader
def load_user(user_id):
    # Query the user from CosmosDB
    query = f"SELECT * FROM c WHERE c.type = 'user' AND c.id = '{user_id}'"
    items = list(container.query_items(query=query, enable_cross_partition_query=True))
    
    if not items:
        return None
    
    user_data = items[0]
    return User(
        id=user_data['id'],
        username=user_data['username'],
        email=user_data['email'],
        password=user_data['password']
    )

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Handle login form submission
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Query the user
        query = f"SELECT * FROM c WHERE c.type = 'user' AND c.username = '{username}'"
        items = list(container.query_items(query=query, enable_cross_partition_query=True))
        
        if not items or not check_password_hash(items[0]['password'], password):
            flash('Please check your login details and try again.')
            return redirect(url_for('auth.login'))
        
        # Create a User instance
        user = User(
            id=items[0]['id'],
            username=items[0]['username'],
            email=items[0]['email'],
            password=items[0]['password']
        )
        
        # Log in the user
        login_user(user)
        return redirect(url_for('dashboard'))
        
    return render_template('login.html')

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    # Handle signup form
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Check if user already exists
        query = f"SELECT * FROM c WHERE c.type = 'user' AND (c.username = '{username}' OR c.email = '{email}')"
        items = list(container.query_items(query=query, enable_cross_partition_query=True))
        
        if items:
            flash('Username or Email already exists')
            return redirect(url_for('auth.signup'))
        
        # Create a new user
        import uuid
        user_id = str(uuid.uuid4())
        new_user = {
            'id': user_id,
            'type': 'user',
            'username': username,
            'email': email,
            'password': generate_password_hash(password)
        }
        
        container.create_item(body=new_user)
        
        return redirect(url_for('auth.login'))
    
    return render_template('signup.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))
