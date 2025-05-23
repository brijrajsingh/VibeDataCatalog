import os
from app import create_app

app = create_app()

if __name__ == '__main__':
    # Get port from environment variable or use 5000 as default
    port = int(os.environ.get("PORT", 5000))
    
    # Run app with host='0.0.0.0' to make it accessible externally
    app.run(host='0.0.0.0', port=port, debug=(os.environ.get('FLASK_ENV') == 'development'))
