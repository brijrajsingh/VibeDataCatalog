import os
from flask import Flask
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_app():
    """Initialize the core application."""
    app = Flask(__name__, instance_relative_config=False)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_key')

    # Initialize plugins
    from .auth import login_manager
    login_manager.init_app(app)

    with app.app_context():
        # Include our routes
        from . import routes
        from . import auth_routes
        from . import api_routes
        
        # Register Blueprints
        from .auth import auth_bp
        from .datasets import datasets_bp
        from .api_routes import api_bp
        from .admin_routes import admin_bp
        
        app.register_blueprint(auth_bp)
        app.register_blueprint(datasets_bp)
        app.register_blueprint(api_bp)
        app.register_blueprint(admin_bp)

        return app
