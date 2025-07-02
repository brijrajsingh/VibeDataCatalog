from flask import render_template, current_app as app
from flask_login import login_required, current_user

@app.route('/')
def index():
    """Landing page."""
    return render_template('index.html')

@app.route('/dashboard')
@login_required
def dashboard():
    """Dashboard page."""
    is_admin = current_user.role == 'admin' if current_user.is_authenticated else False
    return render_template('dashboard.html', is_admin=is_admin)
