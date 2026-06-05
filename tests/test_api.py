import json
import pytest

def test_filters(client):
    resp = client.get('/api/filters')
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'categories' in data
    assert 'steering' in data

def test_cars(client):
    resp = client.get('/api/cars')
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)

def test_cars_with_filters(client):
    resp = client.get('/api/cars?category_id=1&in_stock_only=true')
    assert resp.status_code == 200

def test_register_and_login(client):
    # Регистрация
    reg_data = {
        'username': 'testuser',
        'password': 'testpass',
        'first_name': 'Test',
        'last_name': 'User',
        'phone': '+123456789',
        'email': 'test@example.com'
    }
    resp = client.post('/api/register', json=reg_data)
    assert resp.status_code == 200
    assert resp.get_json()['success'] is True

    # Логин
    login_data = {'username': 'testuser', 'password': 'testpass'}
    resp = client.post('/api/login', json=login_data)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is True
    assert data['role'] == 'user'

    # Проверка текущего пользователя
    resp = client.get('/api/current_user')
    assert resp.status_code == 200
    assert resp.get_json()['authenticated'] is True

    # Логаут
    resp = client.post('/api/logout')
    assert resp.status_code == 200

def test_get_customers_requires_auth(client):
    resp = client.get('/api/customers')
    assert resp.status_code == 401

def test_finalize_sale(client):
    # Сначала логинимся как существующий пользователь (например, из init_data)
    login_data = {'username': 'ivan', 'password': 'ivan'}
    resp = client.post('/api/login', json=login_data)
    assert resp.status_code == 200
    # Получаем список автомобилей, берём id первого
    resp = client.get('/api/cars')
    cars = resp.get_json()
    if not cars:
        pytest.skip('Нет автомобилей в БД')
    car_id = cars[0]['id']
    # Корзина
    cart = [{'id': car_id, 'quantity': 1}]
    # Выбираем менеджера (существующий сотрудник)
    resp = client.get('/api/employees')
    employees = resp.get_json()
    assert len(employees) > 0
    employee_id = employees[0]['id']
    # Оформляем заказ
    order_data = {'cart': cart, 'id_employee': employee_id}
    resp = client.post('/api/finalize_sale', json=order_data)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is True
    assert 'sale_id' in data

def test_top_sales(client):
    # Логинимся как обычный пользователь (топ продаж доступен всем авторизованным)
    login_data = {'username': 'ivan', 'password': 'ivan'}
    client.post('/api/login', json=login_data)
    resp = client.get('/api/top_sales')
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)

def test_report_requires_manager(client):
    # логин как обычный пользователь
    client.post('/api/login', json={'username': 'ivan', 'password': 'ivan'})
    resp = client.get('/api/report?date=2026-01-01')
    assert resp.status_code == 403