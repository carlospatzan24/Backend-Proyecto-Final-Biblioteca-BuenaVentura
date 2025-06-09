from flask import Flask
from flask_cors import CORS
from .config import Config
from .models import db
from .schemas import ma
from .routes import auth_bp, users_bp, roles_bp, books_bp, clientes_bp, prestamos_bp, reportes_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    CORS(app)
    
    db.init_app(app)
    ma.init_app(app)
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(roles_bp)
    app.register_blueprint(books_bp)
    app.register_blueprint(clientes_bp)
    app.register_blueprint(prestamos_bp)
    app.register_blueprint(reportes_bp)
    
    return app