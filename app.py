from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from flask_migrate import Migrate
from datetime import datetime
from sqlalchemy import func, case
import pandas as pd
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os

from models import db, Warehouse, Zone, Item, StockEntry 

app = Flask(__name__)

# Set up database path
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(basedir, 'wms.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'your-secret-key' 

db.init_app(app)  
migrate = Migrate(app, db)  


@app.route('/')
def dashboard():
    items = Item.query.all()
    warehouses = Warehouse.query.all()

     # count all stock entries
    total_entries = StockEntry.query.count()

    # count all ledger rows (same as total_entries unless you have a distinct ledger model)
    stock_ledger_count = StockEntry.query.count()

     # compute stock balance
    stock_balance_raw = db.session.query(
         Item.name,
         Warehouse.name,
         func.sum(
             case(
                 (StockEntry.type == 'IN', StockEntry.quantity),
                 else_=-StockEntry.quantity
             )
         ).label('balance')
     ).join(Item, Item.id == StockEntry.item_id)\
      .join(Warehouse, Warehouse.id == StockEntry.warehouse_id)\
      .group_by(Item.name, Warehouse.name).all()

    stock_balance = [
         {"item": item, "warehouse": warehouse, "balance": balance}
         for item, warehouse, balance in stock_balance_raw
     ]

    return render_template(
        'dashboard.html',
        items=items,
        warehouses=warehouses,
        stock_entries_count=total_entries,
        stock_ledger_count=stock_ledger_count,   # ← pass it here
        stock_balance=stock_balance
)

@app.route('/items', methods=['GET', 'POST'])
def items():
    # If form posted:
    if request.method == 'POST':
        item_id = request.form.get('item_id')
        name = request.form['name']
        unit = request.form['unit']
        description = request.form['description']

        if not name:
            flash("Name is required.")
            return redirect(url_for('items'))

        if item_id:
            # EDIT existing
            item = Item.query.get_or_404(item_id)
            item.name = name
            item.unit = unit
            item.description = description
            flash("Item updated.")
        else:
            # ADD new
            item = Item(name=name, unit=unit, description=description)
            db.session.add(item)
            flash("Item added.")

        db.session.commit()
        return redirect(url_for('items'))

    # For GET: check if we're in “edit” mode
    edit_id = request.args.get('edit_id', type=int)
    edit_item = Item.query.get(edit_id) if edit_id else None

    # Finally render the page
    items_list = Item.query.all()
    return render_template('items.html',
                           items=items_list,
                           edit_item=edit_item)

@app.route('/warehouses', methods=['GET', 'POST'])
def warehouses():
    if request.method == 'POST':
        wh_id     = request.form.get('warehouse_id')
        name      = request.form.get('warehouse_name')
        hierarchy = request.form.get('hierarchy')

        if not name or not hierarchy:
            flash("Name and hierarchy are required.")
            return redirect(url_for('warehouses'))

        if wh_id:
            wh = Warehouse.query.get_or_404(wh_id)
            wh.name      = name
            wh.hierarchy = hierarchy
            flash("Warehouse updated.")
        else:
            wh = Warehouse(name=name, hierarchy=hierarchy)
            db.session.add(wh)
            flash("Warehouse added.")

        db.session.commit()
        return redirect(url_for('warehouses'))

    # GET
    edit_id = request.args.get('edit_id', type=int)
    edit_wh = Warehouse.query.get(edit_id) if edit_id else None
    wh_list = Warehouse.query.all()
    return render_template('warehouses.html',
                           warehouses=wh_list,
                           edit_wh=edit_wh)

@app.route('/zones', methods=['GET', 'POST'])
def zones():
    warehouses = Warehouse.query.all()

    if request.method == 'POST':
        name = request.form['name']
        warehouse_id = request.form['warehouse_id']
        if name and warehouse_id:
            zone = Zone(name=name, warehouse_id=warehouse_id)
            db.session.add(zone)
            db.session.commit()
            flash("Zone added.")
        return redirect(url_for('zones'))

    all_zones = Zone.query.all()
    return render_template('zones.html', zones=all_zones, warehouses=warehouses)

@app.route('/stock_entries', methods=['GET', 'POST'])
def stock_entries():
    entry_id = request.args.get('edit')
    edit_entry = StockEntry.query.get(entry_id) if entry_id else None

    # Handle POST (add/edit)
    if request.method == 'POST':
        if request.form.get('entry_id'):  # Editing
            entry = StockEntry.query.get(request.form['entry_id'])
            entry.item_id = request.form['item_id']
            entry.quantity = request.form['quantity']
            entry.type = request.form['type']
            entry.warehouse_id = request.form['warehouse_id']
        else:
            entry = StockEntry(
                item_id=request.form['item_id'],
                quantity=request.form['quantity'],
                type=request.form['type'],
                warehouse_id=request.form['warehouse_id'],
                date=datetime.utcnow()
            )
            db.session.add(entry)
        db.session.commit()
        return redirect(url_for('stock_entries'))

    # Filtering
    query = StockEntry.query

    item_filter = request.args.get('item')
    if item_filter:
        query = query.join(Item).filter(Item.name.ilike(f"%{item_filter}%"))

    warehouse_filter = request.args.get('warehouse')
    if warehouse_filter:
        query = query.join(Warehouse).filter(Warehouse.name.ilike(f"%{warehouse_filter}%"))

    start_date = request.args.get('start')
    end_date = request.args.get('end')
    if start_date:
        query = query.filter(StockEntry.date >= datetime.strptime(start_date, "%Y-%m-%d"))
    if end_date:
        query = query.filter(StockEntry.date <= datetime.strptime(end_date, "%Y-%m-%d"))

    stock_entries = query.order_by(StockEntry.date.desc()).all()
    items = Item.query.all()
    warehouses = Warehouse.query.all()

    return render_template(
        'stock_entries.html',
        stock_entries=stock_entries,
        items=items,
        warehouses=warehouses,
        edit_entry=edit_entry
    )


@app.route('/export_stock_entries')
def export_stock_entries():
    format = request.args.get('format', 'excel')
    entries = StockEntry.query.all()

    if format == 'excel':
        # Prepare data
        data = [{
            'Date': entry.date.strftime('%Y-%m-%d %H:%M') if entry.date else 'N/A',
            'Item': entry.item.name,
            'Type': entry.type,
            'Quantity': entry.quantity,
            'Warehouse': entry.warehouse.name
        } for entry in entries]

        # Create DataFrame
        df = pd.DataFrame(data)

        # Save to Excel in-memory
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='StockEntries')
        output.seek(0)

        return send_file(output, download_name="stock_entries.xlsx", as_attachment=True)

    elif format == 'pdf':
        output = BytesIO()
        p = canvas.Canvas(output, pagesize=letter)
        width, height = letter

        p.setFont("Helvetica", 12)
        y = height - 40
        p.drawString(40, y, "Stock Entries Report")
        y -= 30

        for i, entry in enumerate(entries, 1):
            line = f"{entry.date.strftime('%Y-%m-%d %H:%M') if entry.date else 'N/A'} - {entry.item.name} - {entry.type} {entry.quantity} in {entry.warehouse.name}"
            p.drawString(40, y, line)
            y -= 18
            if y < 50:
                p.showPage()
                p.setFont("Helvetica", 12)
                y = height - 40

        p.save()
        output.seek(0)
        return send_file(output, download_name="stock_entries.pdf", as_attachment=True)

    return "Invalid format.", 400

@app.route('/edit_stock_entry/<int:entry_id>', methods=['GET', 'POST'])
def edit_stock_entry(entry_id):
    entry = StockEntry.query.get_or_404(entry_id)

    if request.method == 'POST':
        entry.quantity = request.form['quantity']
        db.session.commit()
    return redirect(url_for('add_stock_entry', entry_id=entry_id))

    # Return the same template with the selected entry passed in for editing
    stock_entries = StockEntry.query.all()
    return render_template('stock_entries.html', stock_entries=stock_entries, edit_entry=entry)

@app.route('/delete_stock_entry/<int:entry_id>')
def delete_stock_entry(entry_id):
    entry = StockEntry.query.get_or_404(entry_id)
    db.session.delete(entry)
    db.session.commit()
    flash("Stock entry deleted.")
    return redirect(url_for('stock_entries'))



@app.route('/add_stock_entry', methods=['GET', 'POST'])
def add_stock_entry():
    items = Item.query.all()
    warehouses_query = Warehouse.query.all()

    # For the form and JS auto-fill
    warehouses = [
        {"id": w.id, "name": w.name, "hierarchy": w.hierarchy}
        for w in warehouses_query
    ]

    if request.method == 'POST':
        item_id = request.form['item_id']
        warehouse_id = request.form['warehouse_id']
        quantity = float(request.form['quantity'])
        entry_type = request.form['type']

        # Optional: validate warehouse exists
        warehouse = Warehouse.query.get(warehouse_id)
        if not warehouse:
            flash("Invalid warehouse selected.")
            return redirect(url_for('add_stock_entry'))

        if entry_type == 'OUT':
            current_balance = db.session.query(
                func.sum(
                    case((StockEntry.type == 'IN', StockEntry.quantity),
                         else_=-StockEntry.quantity)
                )
            ).filter_by(item_id=item_id, warehouse_id=warehouse_id).scalar() or 0

            if quantity > current_balance:
                flash("Not enough stock available!")
                return redirect(url_for('add_stock_entry'))

        # Create stock entry
        new_entry = StockEntry(
            item_id=item_id,
            warehouse_id=warehouse_id,
            quantity=quantity,
            type=entry_type
        )
        db.session.add(new_entry)
        db.session.commit()

        flash("Stock entry recorded.")
        return redirect(url_for('stock_entries'))

    return render_template(
        'stock_entry_form.html',
        items=items,
        warehouses=warehouses
    )

@app.route('/stock_ledger')
def stock_ledger():
    start = request.args.get('start')
    end = request.args.get('end')
    query = StockEntry.query
    if start and end:
        query = query.filter(StockEntry.date.between(start, end))
    entries = query.order_by(StockEntry.date.desc()).all()
    return render_template('stock_ledger.html', entries=entries)


@app.route('/stock_balance')
def stock_balance():
    # Aggregate IN vs OUT
    raw = db.session.query(
        Item.name.label('item'),
        Warehouse.name.label('warehouse'),
        func.sum(
            case(
                (StockEntry.type == 'IN', StockEntry.quantity),
                else_=-StockEntry.quantity
            )
        ).label('balance')
    ).join(Item, Item.id == StockEntry.item_id)\
     .join(Warehouse, Warehouse.id == StockEntry.warehouse_id)\
     .group_by(Item.name, Warehouse.name).all()

    balances = [dict(item=i, warehouse=w, balance=b) for i, w, b in raw]
    return render_template(
        'stock_balance.html',
        stock_balance=balances,
        active='stock_balance'
    )

@app.route('/edit_item/<int:item_id>', methods=['GET', 'POST'])
def edit_item(item_id):
    item = Item.query.get_or_404(item_id)
    if request.method == 'POST':
        item.name = request.form['name']
        item.unit = request.form['unit']
        item.description = request.form['description']
        db.session.commit()
        flash("Item updated.")
        return redirect(url_for('view_items'))
    return render_template('edit_item.html', item=item)

@app.route('/delete_item/<int:item_id>', methods=['POST'])
def delete_item(item_id):
    item = Item.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash("Item deleted.")
    return redirect(url_for('items'))

@app.route('/edit_warehouse/<int:warehouse_id>', methods=['GET', 'POST'])
def edit_warehouse(warehouse_id):
    wh = Warehouse.query.get_or_404(warehouse_id)
    if request.method == 'POST':
        wh.name = request.form['warehouse_name']
        db.session.commit()
        flash("Warehouse updated.")
        return redirect(url_for('view_warehouses'))
    return render_template('edit_warehouse.html', warehouse=wh)

@app.route('/delete_warehouse/<int:warehouse_id>', methods=['POST'])
def delete_warehouse(warehouse_id):
    wh = Warehouse.query.get_or_404(warehouse_id)
    db.session.delete(wh)
    db.session.commit()
    flash("Warehouse deleted.")
    return redirect(url_for('warehouses'))

@app.route('/download_stock_report')
def download_stock_report():
    # Query the stock balance
    stock_balance_raw = db.session.query(
        Item.name.label('Item'),
        Warehouse.name.label('Warehouse'),
        func.sum(
            case((StockEntry.type == 'IN', StockEntry.quantity), else_=-StockEntry.quantity)
        ).label('Balance')
    ).join(Item, Item.id == StockEntry.item_id)\
     .join(Warehouse, Warehouse.id == StockEntry.warehouse_id)\
     .group_by(Item.name, Warehouse.name)\
     .all()

    # Convert to DataFrame
    df = pd.DataFrame(stock_balance_raw, columns=['Item', 'Warehouse', 'Balance'])

    # Save to an in-memory Excel file
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Stock Balance', index=False)
    output.seek(0)

    # Send the Excel file
    return send_file(output,
                     as_attachment=True,
                     download_name="stock_balance_report.xlsx",
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


# Logout
@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out.")
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)