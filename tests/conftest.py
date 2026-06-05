import sys
import os
import pytest
import tempfile

# Добавляем корень проекта в путь импорта (там лежит папка autodealer)
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from autodealer import create_app

@pytest.fixture
def app(monkeypatch):
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    monkeypatch.setattr('autodealer.db_queries.DB_NAME', db_path)
    app = create_app()
    app.config['TESTING'] = True
    import autodealer.db_queries as dbq
    with app.app_context():
        conn = dbq.get_db()
        dbq.init_db(conn, 'schema.sql', 'init_data.csv', dbq.load_initial_data)
        conn.close()
    yield app
    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def db_conn(app):
    import autodealer.db_queries as dbq
    conn = dbq.get_db()
    yield conn
    conn.close()