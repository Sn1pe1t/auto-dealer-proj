from autodealer import create_app
from autodealer.db_queries import get_db, init_db, load_initial_data

if __name__ == '__main__':
    app = create_app()
    # Инициализация БД при старте
    conn = get_db()
    init_db(conn, 'schema.sql', 'init_data.csv', load_initial_data)
    conn.close()
    app.run(debug=True, host='0.0.0.0', port=5000)