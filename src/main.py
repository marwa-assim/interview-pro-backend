import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from datetime import timedelta

from src.models.user import db
from src.routes.user import user_bp
from src.routes.auth import auth_bp
from src.routes.interview import interview_bp
from src.routes.cv import cv_bp
from src.routes.business_card import business_card_bp
from src.routes.admin import admin_bp

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))

# Configuration
app.config['SECRET_KEY'] = 'interview-platform-secret-key-2024'
app.config['JWT_SECRET_KEY'] = 'jwt-secret-string-interview-platform'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URL', 
    f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
CORS(app, origins="*")
jwt = JWTManager(app)
migrate = Migrate(app, db)

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(user_bp, url_prefix='/api/users')
app.register_blueprint(interview_bp, url_prefix='/api/interviews')
app.register_blueprint(cv_bp, url_prefix='/api/cv')
app.register_blueprint(business_card_bp, url_prefix='/api/business-cards')
app.register_blueprint(admin_bp, url_prefix='/api/admin')

# Initialize database
db.init_app(app)
with app.app_context():
    db.create_all()

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    static_folder_path = app.static_folder
    if static_folder_path is None:
            return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return "index.html not found", 404


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
