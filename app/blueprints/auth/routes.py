from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.models.donor import BLOOD_TYPES
from app.services.auth_service import (
    register_user, authenticate_user, login_user_session, logout_user_session,
    get_current_user, role_required
)

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if get_current_user():
        return redirect(url_for('auth.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        success, message, user = authenticate_user(email, password)
        if success and user:
            login_user_session(user)
            flash(f"Welcome back, {user.name}!", "success")
            next_url = request.args.get('next')
            if next_url and next_url.startswith('/'):
                return redirect(next_url)
            return redirect(url_for('auth.dashboard'))
        else:
            flash(message, "danger")

    return render_template('auth/login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if get_current_user():
        return redirect(url_for('auth.dashboard'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        role = request.form.get('role', '')

        profile_data = {
            'blood_type': request.form.get('blood_type'),
            'date_of_birth': request.form.get('date_of_birth'),
            'organization_name': request.form.get('organization_name'),
            'contact_phone': request.form.get('contact_phone')
        }

        success, message, user_data = register_user(name, email, password, role, profile_data)
        if success:
            flash(message + " Please log in with your credentials.", "success")
            return redirect(url_for('auth.login'))
        else:
            flash(message, "danger")

    return render_template('auth/register.html', blood_types=BLOOD_TYPES)


@auth_bp.route('/logout')
def logout():
    logout_user_session()
    flash("You have been securely logged out.", "info")
    return redirect(url_for('auth.login'))


@auth_bp.route('/dashboard')
def dashboard():
    user = get_current_user()
    if not user:
        return redirect(url_for('auth.login'))

    if user.role == 'admin':
        return redirect(url_for('admin.dashboard'))
    elif user.role == 'donor':
        return redirect(url_for('donors.dashboard'))
    elif user.role == 'requester':
        return redirect(url_for('requests.my_requests'))

    return redirect(url_for('inventory.live_view'))
