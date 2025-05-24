from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Item(db.Model):
    __tablename__ = 'item'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    unit = db.Column(db.String(20))
    description = db.Column(db.Text)
    stock_entries = db.relationship('StockEntry', back_populates='item')


class Warehouse(db.Model):
    __tablename__ = 'warehouse'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    hierarchy = db.Column(db.String(50))
    zones = db.relationship("Zone", back_populates="warehouse")
    stock_entries = db.relationship('StockEntry', back_populates='warehouse')



class Zone(db.Model):
    __tablename__ = 'zone'
    id = db.Column(db.Integer, primary_key=True)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouse.id'))
    warehouse = db.relationship("Warehouse", back_populates="zones")


class StockEntry(db.Model):
    __tablename__ = 'stock_entry'
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouse.id'), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    type = db.Column(db.String(20))
    date = db.Column(db.DateTime)
    date = db.Column(db.DateTime, default=datetime.utcnow)  # ← add default

    item = db.relationship('Item', back_populates='stock_entries')
    warehouse = db.relationship('Warehouse', back_populates='stock_entries')
