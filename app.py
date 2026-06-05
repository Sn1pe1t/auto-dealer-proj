# app.py
from flask import Flask
import secrets
from app.routes import api

def create_app():
    app = Flask(__name__)
    app.secret_key = secrets.token_hex(32)
    app.register_blueprint(api)
    return app

if __name__ == '__main__':
    app = create_app()
    # Инициализация БД (можно вынести отдельно)
    from app.db_queries import get_db, init_db, load_initial_data
    db_conn = get_db()
    init_db(db_conn, 'schema.sql', 'init_data.csv', load_initial_data)
    db_conn.close()
    app.run(debug=True, host='0.0.0.0', port=5000)