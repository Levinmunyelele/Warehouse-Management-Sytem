import pytest
from app import app, db
from models import Warehouse, Item, StockEntry
from flask import url_for

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client

# Helper to create test data
def create_sample_data():
    wh = Warehouse(name='Main WH', hierarchy='Region A')
    item = Item(name='Test Item', unit='pcs', description='Test Description')
    db.session.add_all([wh, item])
    db.session.commit()
    return item, wh

def test_dashboard(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b"Stock" in response.data or b"Item" in response.data  # adjust based on your template

def test_add_item(client):
    response = client.post('/items', data={
        'name': 'New Item',
        'unit': 'box',
        'description': 'A test item'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b"Item added." in response.data

def test_edit_item(client):
    item = Item(name='Old Item', unit='kg', description='desc')
    db.session.add(item)
    db.session.commit()

    response = client.post('/items', data={
        'item_id': item.id,
        'name': 'Updated Item',
        'unit': 'litre',
        'description': 'new desc'
    }, follow_redirects=True)
    
    assert b"Item updated." in response.data

def test_add_stock_entry(client):
    item, wh = create_sample_data()

    response = client.post('/stock_entries', data={
        'item_id': item.id,
        'warehouse_id': wh.id,
        'quantity': 10,
        'type': 'IN'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert StockEntry.query.count() == 1

def test_export_stock_entries_excel(client):
    create_sample_data()
    response = client.get('/export_stock_entries?format=excel')
    assert response.status_code == 200
    assert response.content_type == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

def test_add_warehouse(client):
    response = client.post('/warehouses', data={
        'warehouse_name': 'Warehouse X',
        'hierarchy': 'Central'
    }, follow_redirects=True)

    assert b"Warehouse added." in response.data

def test_delete_stock_entry(client):
    item, wh = create_sample_data()
    entry = StockEntry(item_id=item.id, warehouse_id=wh.id, quantity=10, type='IN')
    db.session.add(entry)
    db.session.commit()

    response = client.get(f'/delete_stock_entry/{entry.id}', follow_redirects=True)
    assert b"Stock entry deleted." in response.data
    assert StockEntry.query.get(entry.id) is None
