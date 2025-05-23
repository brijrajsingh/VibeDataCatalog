from flask import render_template, current_app as app
from flask_login import login_required

@app.route('/')
def index():
    """Landing page."""
    return render_template('index.html')

@app.route('/dashboard')
@login_required
def dashboard():
    """Dashboard page."""
    return render_template('dashboard.html')
