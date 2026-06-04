"""
AutoDealer Core - библиотека для управления системой автосалона.

Основные компоненты:
- database: инициализация и загрузка БД
- models: бизнес-логика и работа с данными
"""

from .database import init_db, load_initial_data
from .models import (
    get_car_info,
    finalize_sale,
    get_report,
    get_sales_list,
    get_sale_details
)

__version__ = '0.1.0'
__author__ = 'AutoDealer Team'
__all__ = [
    'init_db',
    'load_initial_data',
    'get_car_info',
    'finalize_sale',
    'get_report',
    'get_sales_list',
    'get_sale_details',
]
