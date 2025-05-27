# Warehouse Management System (WMS)
=================================

### Overview
---
This Warehouse Management System is a lightweight inventory tracking solution built with **Flask** and **SQLAlchemy**. It's designed to manage stock entries (IN/OUT), track current stock balances, and visualize the structure of warehouses organized in a hierarchy: National > Regional > Zone > Subzone.

### Features
---
* CRUD operations for **Items** and **Warehouses**
* Hierarchical structure: **National > Regional > Zone > Subzone**
* Stock entry tracking (IN/OUT) for each warehouse
* Dynamic stock balance computation
* Dashboard displaying:
    * Total items
    * Total warehouses
    * Total stock entries
    * Current stock balances grouped by item and warehouse
* Export stock balances to:
    * **PDF**
    * **Excel**

### Technologies Used
---
* **Python 3.x**
* **Flask**
* **SQLAlchemy** (ORM)
* **Jinja2** (templating)
* **SQLite** (can be replaced with PostgreSQL/MySQL)
* **Bootstrap** (for frontend UI)
* `openpyxl`, `pandas`, `reportlab` (for PDF/Excel export)

### Project Structure
---
Project Structure
-----------------
.
├── app.py                  # Main Flask app
├── models.py               # SQLAlchemy models (Item, Warehouse, Zone, StockEntry)
├── templates/              # Jinja2 HTML templates
├── static/                 # Static files (CSS, JS)
├── exports/                # PDF and Excel export files
└── migrations/             # Alembic migration files

### Database Models
---
* **Item**: `id`, `name`, `unit`, `description`
* **Warehouse**: `id`, `name`, `hierarchy`
* **Zone**: `id`, `warehouse_id`
* **StockEntry**: `id`, `item_id`, `warehouse_id`, `quantity`, `type`, `date`

### Usage Instructions
---
1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/Levinmunyelele/Warehouse-Management-System.git](https://github.com/Levinmunyelele/Warehouse-Management-System.git)
    cd Warehouse-Management-System
    ```

2.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Initialize the Database:**
    ```bash
    flask db init
    flask db migrate -m "Initial migration"
    flask db upgrade
    ```

4.  **Run the Application:**
    ```bash
    flask run
    ```
    Visit `http://127.0.0.1:5000` in your browser to access the dashboard.

### Future Improvements
---
* User authentication with roles (e.g., admin, manager)
* Reports and charts
* Stock thresholds and alerts
* RESTful API support

---

### Author
---
**Levin Munyelele**
* Email: munyelelelevin@gmail.com
* GitHub: [https://github.com/Levinmunyelele](https://github.com/Levinmunyelele)

---

### License
---
This project is licensed under the [MIT License](LICENSE).