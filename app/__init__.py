from datetime import datetime

from flask import Flask, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf import CSRFProtect

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = '请先登录'
csrf = CSRFProtect()


def create_app():
    app = Flask(__name__)
    app.config.from_object('app.config.Config')

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    from app.auth import auth_bp
    from app.survey import survey_bp
    from app.response import response_bp
    from app.stats import stats_bp
    from app.admin import admin_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(survey_bp, url_prefix='/survey')
    app.register_blueprint(response_bp, url_prefix='/response')
    app.register_blueprint(stats_bp, url_prefix='/stats')
    app.register_blueprint(admin_bp, url_prefix='/admin')

    @app.route('/')
    def index():
        return redirect(url_for('survey.list_surveys'))

    @app.context_processor
    def inject_now():
        return {'now': datetime.now()}

    with app.app_context():
        db.create_all()

    return app
