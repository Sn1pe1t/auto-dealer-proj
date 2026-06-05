import os
from flask import Flask
import secrets
from autodealer.routes import api

def create_app():
    # Явно указываем папку с шаблонами
    template_dir = os.path.join(os.path.dirname(__file__), 'templates')
    app = Flask(__name__, template_folder=template_dir)
    app.secret_key = secrets.token_hex(32)
    app.register_blueprint(api)
    return app