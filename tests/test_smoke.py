import os

def test_schema_file_exists():
    assert os.path.exists('schema.sql'), "schema.sql not found"

def test_init_data_exists():
    assert os.path.exists('init_data.csv'), "init_data.csv not found"

def test_app_module_exists():
    assert os.path.exists('run.py'), "run.py not found"

def test_templates_exist():
    assert os.path.exists('autodealer/templates/index.html'), "templates/index.html not found"