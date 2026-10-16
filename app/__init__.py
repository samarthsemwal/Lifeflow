import os
from flask import Flask, render_template, jsonify, request, redirect, url_for
from app.config import config_by_name
from app.extensions import db
from app.services.auth_service import get_current_user

def create_app(config_name: str = None) -> Flask:
    """
    Application factory pattern creating configured Flask application instance.
    """
    app = Flask(__name__)

    env_name = config_name or os.getenv('FLASK_ENV', 'development')
    app_config = config_by_name.get(env_name, config_by_name['default'])
    app.config.from_object(app_config)

    # Initialize extensions
    db.init_app(app)

    # Context processor to make active user available in all Jinja templates
    @app.context_processor
    def inject_user():
        return dict(current_user=get_current_user())

    # Root route redirect based on authentication
    @app.route('/')
    def index():
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

    # Register Blueprints
    from app.blueprints.auth.routes import auth_bp
    from app.blueprints.donors.routes import donors_bp
    from app.blueprints.requests.routes import requests_bp
    from app.blueprints.inventory.routes import inventory_bp
    from app.blueprints.admin.routes import admin_bp
    from app.blueprints.api.routes import api_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(donors_bp, url_prefix='/donors')
    app.register_blueprint(requests_bp, url_prefix='/requests')
    app.register_blueprint(inventory_bp, url_prefix='/inventory')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(api_bp, url_prefix='/api')

    # Global Error Handlers
    @app.errorhandler(400)
    def bad_request(e):
        if request.path.startswith('/api/') or request.is_json:
            return jsonify({'success': False, 'error': str(e)}), 400
        return render_template('errors/400.html', error=e), 400

    @app.errorhandler(401)
    def unauthorized(e):
        if request.path.startswith('/api/') or request.is_json:
            return jsonify({'success': False, 'error': 'Unauthorized: Authentication required.'}), 401
        return redirect(url_for('auth.login'))

    @app.errorhandler(403)
    def forbidden(e):
        if request.path.startswith('/api/') or request.is_json:
            return jsonify({'success': False, 'error': 'Forbidden: Insufficient privileges.'}), 403
        return render_template('errors/403.html', error=e), 403

    @app.errorhandler(404)
    def not_found(e):
        if request.path.startswith('/api/') or request.is_json:
            return jsonify({'success': False, 'error': 'Resource not found.'}), 404
        return render_template('errors/404.html', error=e), 404

    @app.errorhandler(500)
    def internal_error(e):
        db.session.rollback()
        if request.path.startswith('/api/') or request.is_json:
            return jsonify({'success': False, 'error': 'An internal server error occurred.'}), 500
        return render_template('errors/500.html', error=e), 500

    # Auto-create tables if running in development / test mode
    with app.app_context():
        try:
            db.create_all()
        except Exception as e:
            app.logger.warning(f"Database auto-creation warning: {e}")

    return app
