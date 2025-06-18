from flask import render_template, current_app as app
from flask_login import current_user

@app.route('/profile')
def profile():
    """User profile page."""
    if not current_user.is_authenticated:
        return render_template('login.html')
    return render_template('auth/profile.html', name=current_user.username)
