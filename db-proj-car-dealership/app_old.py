import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
from collections import defaultdict
import csv
import os

DB_NAME = 'autodealer.db'
SCHEMA_FILE = 'schema.sql'
INIT_DATA_FILE = 'init_data.csv'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON")

    if os.path.exists(SCHEMA_FILE):
        with open(SCHEMA_FILE, 'r', encoding='utf-8') as f:
            conn.executescript(f.read())
        conn.commit()
    else:
        messagebox.showerror("РћС€РёР±РєР°", f"Р¤Р°Р№Р» {SCHEMA_FILE} РЅРµ РЅР°Р№РґРµРЅ.")
        conn.close()
        raise SystemExit

    # РЈРґР°Р»СЏРµРј СЃС‚Р°СЂС‹Р№ С‚СЂРёРіРіРµСЂ, РµСЃР»Рё РѕРЅ РѕСЃС‚Р°Р»СЃСЏ (РЅР° РІСЃСЏРєРёР№ СЃР»СѓС‡Р°Р№)
    conn.execute("DROP TRIGGER IF EXISTS deduct_quantity")

    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM cars")
    if cur.fetchone()[0] == 0:
        if os.path.exists(INIT_DATA_FILE):
            load_initial_data(conn, INIT_DATA_FILE)
        else:
            messagebox.showwarning("РџСЂРµРґСѓРїСЂРµР¶РґРµРЅРёРµ", f"Р¤Р°Р№Р» {INIT_DATA_FILE} РѕС‚СЃСѓС‚СЃС‚РІСѓРµС‚. Р”Р°РЅРЅС‹Рµ РЅРµ Р·Р°РіСЂСѓР¶РµРЅС‹.")

    return conn

def load_initial_data(conn, csv_file):
    table_columns = {
        'steering_types': ['id', 'name'],
        'fuel_types': ['id', 'name'],
        'transmissions': ['id', 'name'],
        'drives': ['id', 'name'],
        'conditions': ['id', 'name'],
        'job_titles': ['id', 'name'],
        'employees': ['id', 'name', 'surname', 'id_job_title'],
        'customers': ['id', 'first_name', 'last_name', 'phone', 'email'],
        'car_categories': ['id', 'name'],
        'cars': ['id', 'brand', 'model', 'year', 'color', 'vin', 'price', 'quantity', 'id_category',
                 'id_steering', 'power', 'engine_volume', 'id_fuel_type', 'id_transmission', 'id_drive', 'id_condition', 'mileage']
    }

    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if not row or row[0].startswith('#'):
                continue
            table = row[0].strip()
            values = row[1:]
            if table not in table_columns:
                continue
            cols = table_columns[table]
            # Р”Р»СЏ cars: РїСЂРµРѕР±СЂР°Р·СѓРµРј РїСѓСЃС‚РѕР№ mileage РІ None
            if table == 'cars' and len(values) >= len(cols):
                if values[-1] == '' or values[-1] is None:
                    values[-1] = None
                else:
                    try:
                        values[-1] = int(values[-1])
                    except:
                        values[-1] = None
            if len(values) != len(cols):
                print(f"РџСЂРѕРїСѓС‰РµРЅР° СЃС‚СЂРѕРєР° РґР»СЏ {table}: РѕР¶РёРґР°Р»РѕСЃСЊ {len(cols)} Р·РЅР°С‡РµРЅРёР№, РїРѕР»СѓС‡РµРЅРѕ {len(values)}")
                continue
            placeholders = ','.join(['?' for _ in cols])
            sql = f"INSERT OR IGNORE INTO {table} ({','.join(cols)}) VALUES ({placeholders})"
            try:
                conn.execute(sql, values)
            except Exception as e:
                print(f"РћС€РёР±РєР° РІСЃС‚Р°РІРєРё РІ {table}: {e} (СЃС‚СЂРѕРєР°: {row})")
    conn.commit()

def get_car_info(conn, car_id):
    row = conn.execute("""
        SELECT c.brand, c.model, c.year, c.color, c.price, c.quantity,
               st.name, c.power, c.engine_volume,
               ft.name, t.name, d.name, cond.name, c.mileage
        FROM cars c
        LEFT JOIN steering_types st ON c.id_steering = st.id
        LEFT JOIN fuel_types ft ON c.id_fuel_type = ft.id
        LEFT JOIN transmissions t ON c.id_transmission = t.id
        LEFT JOIN drives d ON c.id_drive = d.id
        LEFT JOIN conditions cond ON c.id_condition = cond.id
        WHERE c.id = ?
    """, (car_id,)).fetchone()
    if row:
        info = {
            "description": f"{row[0]} {row[1]}",
            "year": row[2],
            "color": row[3],
            "price": row[4],
            "stock": row[5],
            "steering": "Р›РµРІС‹Р№" if row[6] == 'left' else "РџСЂР°РІС‹Р№",
            "power": row[7],
            "engine_volume": row[8],
            "fuel_type": row[9] or "",
            "transmission": row[10] or "",
            "drive": row[11] or "",
            "condition": "РќРѕРІС‹Р№" if row[12] == 'new' else "РЎ РїСЂРѕР±РµРіРѕРј" if row[12] == 'used' else row[12],
            "mileage": row[13],
            "in_stock": row[5] > 0
        }
        return info
    return None

def finalize_sale(conn, cart_items, id_employee, id_customer):
    cur = conn.cursor()
    try:
        # Р“СЂСѓРїРїРёСЂСѓРµРј РїРѕР·РёС†РёРё РїРѕ car_id
        totals = defaultdict(int)
        for item in cart_items:
            totals[item['car_id']] += item['quantity']

        sale_items = []
        # РџСЂРѕРІРµСЂСЏРµРј РѕСЃС‚Р°С‚РєРё Рё РіРѕС‚РѕРІРёРј Р·Р°РїРёСЃРё (РЅР°Р»РёС‡РёРµ / РїСЂРµРґР·Р°РєР°Р·)
        for car_id, total_qty in totals.items():
            stock, price = cur.execute(
                "SELECT quantity, price FROM cars WHERE id = ?", (car_id,)
            ).fetchone()
            deduct_qty = min(total_qty, stock)
            preorder_qty = total_qty - deduct_qty

            if deduct_qty > 0:
                sale_items.append((car_id, deduct_qty, price, 1))   # РІ РЅР°Р»РёС‡РёРё
            if preorder_qty > 0:
                sale_items.append((car_id, preorder_qty, price, 0)) # РїСЂРµРґР·Р°РєР°Р·

        total_amount = sum(qty * price for (_, qty, price, _) in sale_items)

        # РЎРѕР·РґР°С‘Рј РїСЂРѕРґР°Р¶Сѓ
        cur.execute(
            "INSERT INTO sales (sale_date, id_customer, id_employee, total_amount) VALUES (?, ?, ?, ?)",
            (datetime.now().timestamp(), id_customer, id_employee, total_amount)
        )
        sale_id = cur.lastrowid

        # Р’СЃС‚Р°РІР»СЏРµРј РґРµС‚Р°Р»Рё Рё СЃРїРёСЃС‹РІР°РµРј РѕСЃС‚Р°С‚РєРё С‚РѕР»СЊРєРѕ РґР»СЏ РїРѕР·РёС†РёР№ РІ РЅР°Р»РёС‡РёРё
        for car_id, qty, price, in_stock_flag in sale_items:
            cur.execute(
                "INSERT INTO sale_details (id_sale, id_car, quantity, price_at_sale, in_stock_at_sale) "
                "VALUES (?, ?, ?, ?, ?)",
                (sale_id, car_id, qty, price, in_stock_flag)
            )
            if in_stock_flag:
                cur.execute(
                    "UPDATE cars SET quantity = quantity - ? WHERE id = ?",
                    (qty, car_id)
                )

        conn.commit()
        return True, sale_id
    except Exception as e:
        conn.rollback()
        return False, str(e)

def get_report(conn, date_str):
    return conn.execute('''
        SELECT c.brand || ' ' || c.model AS car,
               SUM(sd.quantity) AS qty,
               SUM(sd.quantity * sd.price_at_sale) AS revenue
        FROM sale_details sd
        JOIN cars c ON sd.id_car = c.id
        JOIN sales s ON sd.id_sale = s.id
        WHERE DATE(s.sale_date, 'unixepoch') = ?
        GROUP BY c.id
        ORDER BY revenue DESC
    ''', (date_str,)).fetchall()

def get_sales_list(conn, limit=50):
    return conn.execute('''
        SELECT s.id, 
               datetime(s.sale_date, 'unixepoch', 'localtime') AS date,
               (c.first_name || ' ' || c.last_name) AS customer,
               (e.name || ' ' || e.surname) AS employee,
               s.total_amount,
               (SELECT MIN(sd2.in_stock_at_sale) FROM sale_details sd2 WHERE sd2.id_sale = s.id) AS all_in_stock
        FROM sales s
        JOIN customers c ON s.id_customer = c.id
        JOIN employees e ON s.id_employee = e.id
        ORDER BY s.sale_date DESC
        LIMIT ?
    ''', (limit,)).fetchall()

def get_sale_details(conn, sale_id):
    return conn.execute("""
        SELECT ca.brand, ca.model, ca.year, ca.engine_volume,
               ft.name, t.name, d.name,
               sd.quantity, sd.price_at_sale,
               (sd.quantity * sd.price_at_sale) AS subtotal,
               sd.id_car, sd.in_stock_at_sale
        FROM sale_details sd
        JOIN cars ca ON sd.id_car = ca.id
        LEFT JOIN fuel_types ft ON ca.id_fuel_type = ft.id
        LEFT JOIN transmissions t ON ca.id_transmission = t.id
        LEFT JOIN drives d ON ca.id_drive = d.id
        WHERE sd.id_sale = ?
    """, (sale_id,)).fetchall()


class AutoDealerApp:
    def __init__(self, root):
        self.conn = init_db()
        self.root = root
        self.root.title("РђРІС‚РѕСЃР°Р»РѕРЅ вЂ“ РЎРёСЃС‚РµРјР° Р·Р°РєР°Р·РѕРІ")
        self.root.geometry("1200x850")
        self.cart = []
        self.cars = {}

        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TNotebook.Tab', padding=[10, 5], font=('Arial', 10, 'bold'))
        style.configure('TLabel', font=('Arial', 10))
        style.configure('TButton', font=('Arial', 10))
        style.configure('Green.TLabel', foreground='green', font=('Arial', 10, 'bold'))
        style.configure('Red.TLabel', foreground='red', font=('Arial', 10, 'bold'))

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)

        self.tab_sale = tk.Frame(self.notebook)
        self.tab_history = tk.Frame(self.notebook)
        self.notebook.add(self.tab_sale, text="РћС„РѕСЂРјР»РµРЅРёРµ Р·Р°РєР°Р·Р°")
        self.notebook.add(self.tab_history, text="Р—Р°РєР°Р·С‹ Рё РѕС‚С‡С‘С‚С‹")

        self._build_sale_tab()
        self._build_history_tab()

        self.refresh_employee_list()
        self.refresh_customer_list()
        self.refresh_categories()
        self.refresh_history_table()

    # ==================== Р’РєР»Р°РґРєР° РѕС„РѕСЂРјР»РµРЅРёСЏ Р·Р°РєР°Р·Р° ====================
    def _build_sale_tab(self):
        # --- РџР°РЅРµР»СЊ СЃРѕС‚СЂСѓРґРЅРёРєР° Рё РєР»РёРµРЅС‚Р° ---
        top_frame = ttk.LabelFrame(self.tab_sale, text="Р”Р°РЅРЅС‹Рµ Р·Р°РєР°Р·Р°", padding=10)
        top_frame.pack(fill='x', padx=10, pady=5)

        ttk.Label(top_frame, text="РњРµРЅРµРґР¶РµСЂ:").grid(row=0, column=0, padx=5, sticky='w')
        self.emp_var = tk.StringVar()
        self.emp_combo = ttk.Combobox(top_frame, textvariable=self.emp_var, state="readonly", width=35)
        self.emp_combo.grid(row=0, column=1, padx=5, pady=2)
        self.emp_combo.bind('<<ComboboxSelected>>', self._on_emp_selected)

        ttk.Label(top_frame, text="РљР»РёРµРЅС‚:").grid(row=0, column=2, padx=5, sticky='w')
        self.cust_var = tk.StringVar()
        self.cust_combo = ttk.Combobox(top_frame, textvariable=self.cust_var, state="readonly", width=35)
        self.cust_combo.grid(row=0, column=3, padx=5, pady=2)

        # --- РџР°РЅРµР»СЊ РІС‹Р±РѕСЂР° Р°РІС‚РѕРјРѕР±РёР»СЏ ---
        car_frame = ttk.LabelFrame(self.tab_sale, text="Р’С‹Р±РѕСЂ Р°РІС‚РѕРјРѕР±РёР»СЏ", padding=10)
        car_frame.pack(fill='x', padx=10, pady=5)

        ttk.Label(car_frame, text="РљР°С‚РµРіРѕСЂРёСЏ:").grid(row=0, column=0, padx=5, sticky='w')
        self.cat_var = tk.StringVar()
        self.cat_combo = ttk.Combobox(car_frame, textvariable=self.cat_var, state="readonly", width=30)
        self.cat_combo.grid(row=0, column=1, padx=5, pady=2)
        self.cat_combo.bind('<<ComboboxSelected>>', self.update_car_list)

        self.in_stock_var = tk.BooleanVar(value=False)
        self.in_stock_check = ttk.Checkbutton(car_frame, text="РўРѕР»СЊРєРѕ РІ РЅР°Р»РёС‡РёРё",
                                              variable=self.in_stock_var,
                                              command=self.update_car_list)
        self.in_stock_check.grid(row=0, column=2, padx=20, sticky='w')

        # Р”РѕРїРѕР»РЅРёС‚РµР»СЊРЅС‹Рµ С„РёР»СЊС‚СЂС‹
        filter_frame = ttk.LabelFrame(car_frame, text="Р”РѕРїРѕР»РЅРёС‚РµР»СЊРЅС‹Рµ С„РёР»СЊС‚СЂС‹", padding=5)
        filter_frame.grid(row=1, column=0, columnspan=3, pady=5, sticky='ew')

        ttk.Label(filter_frame, text="Р СѓР»СЊ:").grid(row=0, column=0, padx=2, sticky='w')
        self.steering_var = tk.StringVar(value='Р’СЃРµ')
        steering_combo = ttk.Combobox(filter_frame, textvariable=self.steering_var,
                                      values=['Р’СЃРµ', 'Р›РµРІС‹Р№', 'РџСЂР°РІС‹Р№'], state="readonly", width=10)
        steering_combo.grid(row=0, column=1, padx=2)
        steering_combo.bind('<<ComboboxSelected>>', lambda e: self.update_car_list())

        ttk.Label(filter_frame, text="РњРѕС‰РЅРѕСЃС‚СЊ (Р».СЃ.):").grid(row=0, column=2, padx=5, sticky='w')
        self.power_from_var = tk.StringVar()
        self.power_from_entry = ttk.Entry(filter_frame, textvariable=self.power_from_var, width=5)
        self.power_from_entry.grid(row=0, column=3, padx=2)
        ttk.Label(filter_frame, text="вЂ”").grid(row=0, column=4)
        self.power_to_var = tk.StringVar()
        self.power_to_entry = ttk.Entry(filter_frame, textvariable=self.power_to_var, width=5)
        self.power_to_entry.grid(row=0, column=5, padx=2)
        self.power_from_entry.bind('<KeyRelease>', lambda e: self.update_car_list())
        self.power_to_entry.bind('<KeyRelease>', lambda e: self.update_car_list())

        ttk.Label(filter_frame, text="РўРѕРїР»РёРІРѕ:").grid(row=0, column=6, padx=5, sticky='w')
        self.fuel_var = tk.StringVar(value='Р’СЃРµ')
        fuel_combo = ttk.Combobox(filter_frame, textvariable=self.fuel_var,
                                  values=['Р’СЃРµ', 'Р‘РµРЅР·РёРЅ', 'Р”РёР·РµР»СЊ', 'Р“РёР±СЂРёРґ', 'Р­Р»РµРєС‚СЂРѕ'],
                                  state="readonly", width=12)
        fuel_combo.grid(row=0, column=7, padx=2)
        fuel_combo.bind('<<ComboboxSelected>>', lambda e: self.update_car_list())

        ttk.Label(filter_frame, text="РљРџРџ:").grid(row=1, column=0, padx=2, sticky='w')
        self.transmission_var = tk.StringVar(value='Р’СЃРµ')
        trans_combo = ttk.Combobox(filter_frame, textvariable=self.transmission_var,
                                   values=['Р’СЃРµ', 'РњРµС…Р°РЅРёРєР°', 'РђРІС‚РѕРјР°С‚', 'Р РѕР±РѕС‚', 'Р’Р°СЂРёР°С‚РѕСЂ'],
                                   state="readonly", width=12)
        trans_combo.grid(row=1, column=1, padx=2, columnspan=2, sticky='w')
        trans_combo.bind('<<ComboboxSelected>>', lambda e: self.update_car_list())

        ttk.Label(filter_frame, text="РџСЂРёРІРѕРґ:").grid(row=1, column=3, padx=2, sticky='w')
        self.drive_var = tk.StringVar(value='Р’СЃРµ')
        drive_combo = ttk.Combobox(filter_frame, textvariable=self.drive_var,
                                   values=['Р’СЃРµ', 'РџРµСЂРµРґРЅРёР№', 'Р—Р°РґРЅРёР№', 'РџРѕР»РЅС‹Р№'],
                                   state="readonly", width=12)
        drive_combo.grid(row=1, column=4, padx=2, columnspan=2, sticky='w')
        drive_combo.bind('<<ComboboxSelected>>', lambda e: self.update_car_list())

        ttk.Label(filter_frame, text="РЎРѕСЃС‚РѕСЏРЅРёРµ:").grid(row=1, column=6, padx=2, sticky='w')
        self.condition_var = tk.StringVar(value='Р’СЃРµ')
        cond_combo = ttk.Combobox(filter_frame, textvariable=self.condition_var,
                                  values=['Р’СЃРµ', 'РќРѕРІС‹Р№', 'РЎ РїСЂРѕР±РµРіРѕРј'],
                                  state="readonly", width=12)
        cond_combo.grid(row=1, column=7, padx=2)
        cond_combo.bind('<<ComboboxSelected>>', lambda e: self.update_car_list())

        # Р’С‹Р±РѕСЂ Р°РІС‚РѕРјРѕР±РёР»СЏ
        ttk.Label(car_frame, text="РђРІС‚РѕРјРѕР±РёР»СЊ:").grid(row=2, column=0, padx=5, sticky='w', pady=5)
        self.car_var = tk.StringVar()
        self.car_combo = ttk.Combobox(car_frame, textvariable=self.car_var, state="readonly", width=70)
        self.car_combo.grid(row=2, column=1, columnspan=2, padx=5, pady=5, sticky='ew')
        self.car_combo.bind('<<ComboboxSelected>>', self._on_car_selected)

        # РЎС‡С‘С‚С‡РёРє РЅР°Р№РґРµРЅРЅС‹С… Р°РІС‚РѕРјРѕР±РёР»РµР№ (РЅРѕРІС‹Р№ СЌР»РµРјРµРЅС‚)
        self.car_count_label = ttk.Label(car_frame, text="", font=('Arial', 9, 'italic'))
        self.car_count_label.grid(row=3, column=0, columnspan=3, pady=(0, 5), sticky='w')

        # РРЅС„РѕСЂРјР°С†РёСЏ РѕР± Р°РІС‚РѕРјРѕР±РёР»Рµ
        info_frame = ttk.Frame(car_frame)
        info_frame.grid(row=4, column=0, columnspan=3, pady=5, sticky='w')
        self.lbl_car_info = tk.Text(info_frame, height=6, width=90, font=('Arial', 9), wrap='word', state='disabled')
        self.lbl_car_info.pack(side='left')
        self.lbl_stock_status = ttk.Label(info_frame, text="", font=('Arial', 10, 'bold'))
        self.lbl_stock_status.pack(side='left', padx=15)

        # Р”РѕР±Р°РІР»РµРЅРёРµ РІ РєРѕСЂР·РёРЅСѓ
        add_frame = ttk.Frame(car_frame)
        add_frame.grid(row=5, column=0, columnspan=3, pady=10)
        ttk.Label(add_frame, text="РљРѕР»РёС‡РµСЃС‚РІРѕ:").pack(side='left', padx=5)
        self.qty_entry = ttk.Entry(add_frame, width=8)
        self.qty_entry.insert(0, "1")
        self.qty_entry.pack(side='left', padx=5)
        ttk.Button(add_frame, text="Р”РѕР±Р°РІРёС‚СЊ РІ РєРѕСЂР·РёРЅСѓ", command=self.add_to_cart).pack(side='left', padx=20)

        # --- РљРѕСЂР·РёРЅР° ---
        cart_frame = ttk.LabelFrame(self.tab_sale, text="РљРѕСЂР·РёРЅР°", padding=10)
        cart_frame.pack(fill='both', expand=True, padx=10, pady=5)

        self.cart_listbox = tk.Listbox(cart_frame, height=8, width=110, font=('Consolas', 10))
        self.cart_listbox.pack(fill='both', expand=True, pady=5)
        self.cart_listbox.bind('<Double-Button-1>', lambda e: self.remove_selected())

        cart_btn_frame = ttk.Frame(cart_frame)
        cart_btn_frame.pack()
        ttk.Button(cart_btn_frame, text="РЈРґР°Р»РёС‚СЊ РІС‹Р±СЂР°РЅРЅРѕРµ", command=self.remove_selected).pack(side='left', padx=5)
        ttk.Button(cart_btn_frame, text="РћС‡РёСЃС‚РёС‚СЊ РєРѕСЂР·РёРЅСѓ", command=self.clear_cart).pack(side='left', padx=5)

        # РљРЅРѕРїРєР° РѕС„РѕСЂРјР»РµРЅРёСЏ Р·Р°РєР°Р·Р°
        ttk.Button(self.tab_sale, text="РћС„РѕСЂРјРёС‚СЊ Р·Р°РєР°Р·", command=self.finalize_purchase).pack(pady=10)

    # ==================== Р’РєР»Р°РґРєР° РёСЃС‚РѕСЂРёРё Р·Р°РєР°Р·РѕРІ ====================
    def _build_history_tab(self):
        columns = ('id', 'date', 'customer', 'employee', 'amount', 'status')
        self.history_tree = ttk.Treeview(self.tab_history, columns=columns, show='headings', height=15)
        self.history_tree.heading('id', text='в„–')
        self.history_tree.heading('date', text='Р”Р°С‚Р° Рё РІСЂРµРјСЏ')
        self.history_tree.heading('customer', text='РљР»РёРµРЅС‚')
        self.history_tree.heading('employee', text='РњРµРЅРµРґР¶РµСЂ')
        self.history_tree.heading('amount', text='РЎСѓРјРјР°')
        self.history_tree.heading('status', text='РЎС‚Р°С‚СѓСЃ')

        self.history_tree.column('id', width=50, anchor='center')
        self.history_tree.column('date', width=150, anchor='center')
        self.history_tree.column('customer', width=180)
        self.history_tree.column('employee', width=180)
        self.history_tree.column('amount', width=120, anchor='e')
        self.history_tree.column('status', width=120, anchor='center')

        self.history_tree.pack(fill='both', expand=True, padx=5, pady=5)

        scrollbar = ttk.Scrollbar(self.tab_history, orient='vertical', command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')

        btn_frame = ttk.Frame(self.tab_history)
        btn_frame.pack(pady=5)
        ttk.Button(btn_frame, text="РћР±РЅРѕРІРёС‚СЊ", command=self.refresh_history_table).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Р”РµС‚Р°Р»Рё Р·Р°РєР°Р·Р°", command=self.show_sale_details).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="РўРѕРї РїСЂРѕРґР°Р¶", command=self.show_top_sales).pack(side='left', padx=5)
        self.history_tree.bind('<Double-1>', lambda e: self.show_sale_details())
        # --- Р—Р°РіСЂСѓР·РєР° CSV Рё РѕС‚С‡С‘С‚С‹ ---
        report_frame = ttk.LabelFrame(self.tab_history, text="РћС‚С‡С‘С‚С‹ Рё Р·Р°РіСЂСѓР·РєР° РґР°РЅРЅС‹С…", padding=10)
        report_frame.pack(fill='x', padx=10, pady=5)

        ttk.Button(report_frame, text="Р—Р°РіСЂСѓР·РёС‚СЊ Р°РІС‚РѕРјРѕР±РёР»Рё РёР· CSV",
                   command=self.load_cars_from_csv).pack(side='left', padx=5)

        report_date_frame = ttk.Frame(report_frame)
        report_date_frame.pack(side='left', padx=20)

        ttk.Button(report_date_frame, text="РЎРµРіРѕРґРЅСЏ",
                   command=lambda: self._display_report(datetime.now().strftime("%Y-%m-%d"))
                   ).pack(side='left', padx=2)
        ttk.Label(report_date_frame, text="Р”Р°С‚Р° (Р“Р“Р“Р“-РњРњ-Р”Р”):").pack(side='left', padx=2)
        self.date_entry = ttk.Entry(report_date_frame, width=12)
        self.date_entry.pack(side='left', padx=2)
        ttk.Button(report_date_frame, text="РџРѕРєР°Р·Р°С‚СЊ",
                   command=lambda: self._display_report(self.date_entry.get().strip())
                   ).pack(side='left', padx=2)

        self.text_area = tk.Text(self.tab_history, height=8, width=100, font=('Consolas', 9))
        self.text_area.pack(fill='x', padx=10, pady=5)

    def refresh_history_table(self):
        for row in self.history_tree.get_children():
            self.history_tree.delete(row)
        sales = get_sales_list(self.conn)
        for sale in sales:
            sale_id, date, cust, emp, amount, all_in_stock = sale
            # РћРїСЂРµРґРµР»СЏРµРј СЃС‚Р°С‚СѓСЃ Р·Р°РєР°Р·Р°
            if all_in_stock is None:
                status = "вЂ”"
            elif all_in_stock == 1:
                status = "Р“РѕС‚РѕРІ Рє РІС‹РґР°С‡Рµ"
            else:
                status = "РџСЂРµРґР·Р°РєР°Р·"
            self.history_tree.insert('', 'end', values=(
                sale_id, date, cust, emp, f"{amount:,.2f} СЂСѓР±.", status
            ))

    def show_sale_details(self):
        selection = self.history_tree.selection()
        if not selection:
            messagebox.showinfo("РРЅС„РѕСЂРјР°С†РёСЏ", "Р’С‹Р±РµСЂРёС‚Рµ Р·Р°РєР°Р· РІ С‚Р°Р±Р»РёС†Рµ.")
            return
        sale_id = self.history_tree.item(selection[0])['values'][0]
        details = get_sale_details(self.conn, sale_id)
        if not details:
            messagebox.showinfo("Р—Р°РєР°Р·", "РќРµС‚ РґР°РЅРЅС‹С… Рѕ СЃРѕСЃС‚Р°РІРµ.")
            return

        win = tk.Toplevel(self.root)
        win.title(f"Р”РµС‚Р°Р»Рё Р·Р°РєР°Р·Р° в„–{sale_id}")
        win.geometry("1050x400")

        # РљРѕР»РѕРЅРєРё СЃ СЂР°СЃС€РёСЂРµРЅРЅРѕР№ РёРЅС„РѕСЂРјР°С†РёРµР№
        columns = ('brand', 'model', 'year', 'engine', 'fuel', 'trans', 'drive',
                   'qty', 'price', 'subtotal', 'status', 'id_car')
        tree = ttk.Treeview(win, columns=columns, show='headings')
        tree.heading('brand', text='РњР°СЂРєР°')
        tree.heading('model', text='РњРѕРґРµР»СЊ')
        tree.heading('year', text='Р“РѕРґ')
        tree.heading('engine', text='Р”РІРёРіР°С‚РµР»СЊ')
        tree.heading('fuel', text='РўРѕРїР»РёРІРѕ')
        tree.heading('trans', text='РљРџРџ')
        tree.heading('drive', text='РџСЂРёРІРѕРґ')
        tree.heading('qty', text='РљРѕР»-РІРѕ')
        tree.heading('price', text='Р¦РµРЅР° Р·Р° РµРґ.')
        tree.heading('subtotal', text='РЎСѓРјРјР°')
        tree.heading('status', text='РЎС‚Р°С‚СѓСЃ')
        tree.heading('id_car', text='')  # СЃРєСЂС‹С‚С‹Р№

        tree.column('brand', width=100)
        tree.column('model', width=100)
        tree.column('year', width=50, anchor='center')
        tree.column('engine', width=80, anchor='center')
        tree.column('fuel', width=80, anchor='center')
        tree.column('trans', width=80, anchor='center')
        tree.column('drive', width=80, anchor='center')
        tree.column('qty', width=60, anchor='center')
        tree.column('price', width=100, anchor='e')
        tree.column('subtotal', width=100, anchor='e')
        tree.column('status', width=100, anchor='center')
        tree.column('id_car', width=0, stretch=False)

        for d in details:
            brand, model, year, eng, fuel, trans, drive, qty, price, subtotal, car_id, in_stock = d
            engine_str = f"{eng} Р»" if eng else "вЂ”"
            fuel_str = {"petrol": "Р‘РµРЅР·РёРЅ", "diesel": "Р”РёР·РµР»СЊ", "hybrid": "Р“РёР±СЂРёРґ", "electric": "Р­Р»РµРєС‚СЂРѕ"}.get(fuel, fuel)
            trans_str = {"manual": "РњРµС…Р°РЅРёРєР°", "automatic": "РђРІС‚РѕРјР°С‚", "robot": "Р РѕР±РѕС‚", "variator": "Р’Р°СЂРёР°С‚РѕСЂ"}.get(trans, trans)
            drive_str = {"front": "РџРµСЂРµРґРЅРёР№", "rear": "Р—Р°РґРЅРёР№", "all": "РџРѕР»РЅС‹Р№"}.get(drive, drive)
            status_str = "Р’ РЅР°Р»РёС‡РёРё" if in_stock else "РџСЂРµРґР·Р°РєР°Р·"
            tree.insert('', 'end', values=(
                brand, model, year, engine_str, fuel_str, trans_str, drive_str,
                qty, f"{price:,.2f}", f"{subtotal:,.2f}", status_str, car_id
            ))

        tree.pack(fill='both', expand=True, padx=5, pady=5)
        tree.bind('<Double-1>', lambda e: self._on_detail_double_click(tree))

    def _on_detail_double_click(self, tree):
        selection = tree.selection()
        if not selection:
            return
        values = tree.item(selection[0])['values']
        car_id = values[-1]
        self.show_car_details(car_id)

    def show_car_details(self, car_id):
        info = get_car_info(self.conn, car_id)
        if not info:
            messagebox.showerror("РћС€РёР±РєР°", "РђРІС‚РѕРјРѕР±РёР»СЊ РЅРµ РЅР°Р№РґРµРЅ.")
            return

        win = tk.Toplevel(self.root)
        win.title(f"РРЅС„РѕСЂРјР°С†РёСЏ РѕР± Р°РІС‚РѕРјРѕР±РёР»Рµ: {info['description']}")
        win.geometry("500x300")

        text = tk.Text(win, wrap='word', font=('Arial', 11))
        text.pack(fill='both', expand=True, padx=10, pady=10)

        lines = [
            f"РњР°СЂРєР°/РњРѕРґРµР»СЊ: {info['description']}",
            f"Р“РѕРґ РІС‹РїСѓСЃРєР°: {info['year']}",
            f"Р¦РІРµС‚: {info['color']}",
            f"Р¦РµРЅР°: {info['price']:,.2f} СЂСѓР±.",
            f"Р СѓР»СЊ: {info['steering']}",
            f"РњРѕС‰РЅРѕСЃС‚СЊ: {info['power']} Р».СЃ.",
            f"РћР±СЉС‘Рј РґРІРёРіР°С‚РµР»СЏ: {info['engine_volume']} Р»" if info['engine_volume'] else "РћР±СЉС‘Рј РґРІРёРіР°С‚РµР»СЏ: РЅРµ СѓРєР°Р·Р°РЅ",
            f"РўРѕРїР»РёРІРѕ: {info['fuel_type']}",
            f"РљРѕСЂРѕР±РєР° РїРµСЂРµРґР°С‡: {info['transmission']}",
            f"РџСЂРёРІРѕРґ: {info['drive']}",
            f"РЎРѕСЃС‚РѕСЏРЅРёРµ: {info['condition']}" + (f", РїСЂРѕР±РµРі: {info['mileage']} РєРј" if info['mileage'] else ""),
            f"РћСЃС‚Р°С‚РѕРє РЅР° СЃРєР»Р°РґРµ: {info['stock']} С€С‚.",
            f"РЎС‚Р°С‚СѓСЃ: {'вњ” Р’ РЅР°Р»РёС‡РёРё' if info['in_stock'] else 'вњ РќРµС‚ РІ РЅР°Р»РёС‡РёРё'}"
        ]
        text.insert(tk.END, "\n".join(lines))
        text.config(state='disabled')

    def show_top_sales(self):
        query = '''
            SELECT c.brand, c.model,
                   SUM(sd.quantity) AS total_qty,
                   SUM(sd.quantity * sd.price_at_sale) AS total_revenue
            FROM sale_details sd
            JOIN cars c ON sd.id_car = c.id
            GROUP BY c.id
            ORDER BY total_qty DESC
            LIMIT 10
        '''
        rows = self.conn.execute(query).fetchall()
        if not rows:
            messagebox.showinfo("РўРѕРї РїСЂРѕРґР°Р¶", "РџРѕРєР° РЅРµС‚ РґР°РЅРЅС‹С… Рѕ РїСЂРѕРґР°Р¶Р°С….")
            return

        win = tk.Toplevel(self.root)
        win.title("РўРѕРї-10 РїСЂРѕРґР°РІР°РµРјС‹С… Р°РІС‚РѕРјРѕР±РёР»РµР№")
        win.geometry("700x350")

        tree = ttk.Treeview(win, columns=('brand', 'model', 'qty', 'revenue'), show='headings')
        tree.heading('brand', text='РњР°СЂРєР°')
        tree.heading('model', text='РњРѕРґРµР»СЊ')
        tree.heading('qty', text='РџСЂРѕРґР°РЅРѕ, С€С‚.')
        tree.heading('revenue', text='Р’С‹СЂСѓС‡РєР°, СЂСѓР±.')

        tree.column('brand', width=150)
        tree.column('model', width=150)
        tree.column('qty', width=100, anchor='center')
        tree.column('revenue', width=150, anchor='e')

        for row in rows:
            brand, model, qty, revenue = row
            tree.insert('', 'end', values=(brand, model, qty, f"{revenue:,.2f}"))

        tree.pack(fill='both', expand=True, padx=5, pady=5)

    # ==================== РћР±С‰РёРµ РјРµС‚РѕРґС‹ ====================
    def refresh_employee_list(self):
        rows = self.conn.execute('''
            SELECT e.id, e.name, e.surname, j.name
            FROM employees e JOIN job_titles j ON e.id_job_title = j.id
        ''').fetchall()
        self.emp_map = {f"{n} {s} ({j})": eid for eid, n, s, j in rows}
        self.emp_combo['values'] = list(self.emp_map.keys())
        if self.emp_map:
            self.emp_combo.current(0)
        self._on_emp_selected()

    def _on_emp_selected(self, _event=None):
        self.current_emp_id = self.emp_map.get(self.emp_var.get())

    def refresh_customer_list(self):
        rows = self.conn.execute(
            "SELECT id, first_name, last_name, phone FROM customers ORDER BY last_name"
        ).fetchall()
        self.cust_map = {f"{fn} {ln} ({ph})": cid for cid, fn, ln, ph in rows}
        self.cust_combo['values'] = list(self.cust_map.keys())
        if self.cust_map:
            self.cust_combo.current(0)

    def refresh_categories(self):
        rows = self.conn.execute(
            "SELECT id, name FROM car_categories ORDER BY name"
        ).fetchall()
        self.cat_map = {name: cid for cid, name in rows}
        self.cat_combo['values'] = list(self.cat_map.keys())
        if self.cat_map:
            self.cat_combo.current(0)
            self.update_car_list()
        else:
            self.car_combo['values'] = []
            self.cars = {}

    def update_car_list(self, _event=None):
        cid = self.cat_map.get(self.cat_var.get()) if self.cat_var.get() else None
        conditions = []
        params = []

        if cid:
            conditions.append("c.id_category = ?")
            params.append(cid)
        if self.in_stock_var.get():
            conditions.append("c.quantity > 0")

        steering = self.steering_var.get()
        if steering == 'Р›РµРІС‹Р№':
            conditions.append("st.name = 'left'")
        elif steering == 'РџСЂР°РІС‹Р№':
            conditions.append("st.name = 'right'")

        power_from = self.power_from_var.get().strip()
        power_to = self.power_to_var.get().strip()
        if power_from:
            try:
                conditions.append("c.power >= ?")
                params.append(int(power_from))
            except: pass
        if power_to:
            try:
                conditions.append("c.power <= ?")
                params.append(int(power_to))
            except: pass

        fuel = self.fuel_var.get()
        fuel_map = {'Р‘РµРЅР·РёРЅ':'petrol','Р”РёР·РµР»СЊ':'diesel','Р“РёР±СЂРёРґ':'hybrid','Р­Р»РµРєС‚СЂРѕ':'electric'}
        if fuel in fuel_map:
            conditions.append("ft.name = ?")
            params.append(fuel_map[fuel])

        trans = self.transmission_var.get()
        trans_map = {'РњРµС…Р°РЅРёРєР°':'manual','РђРІС‚РѕРјР°С‚':'automatic','Р РѕР±РѕС‚':'robot','Р’Р°СЂРёР°С‚РѕСЂ':'variator'}
        if trans in trans_map:
            conditions.append("tr.name = ?")
            params.append(trans_map[trans])

        drive = self.drive_var.get()
        drive_map = {'РџРµСЂРµРґРЅРёР№':'front','Р—Р°РґРЅРёР№':'rear','РџРѕР»РЅС‹Р№':'all'}
        if drive in drive_map:
            conditions.append("d.name = ?")
            params.append(drive_map[drive])

        cond = self.condition_var.get()
        cond_map = {'РќРѕРІС‹Р№':'new','РЎ РїСЂРѕР±РµРіРѕРј':'used'}
        if cond in cond_map:
            conditions.append("cond.name = ?")
            params.append(cond_map[cond])

        query = """
            SELECT c.id, c.brand, c.model, c.year, c.price, c.quantity
            FROM cars c
            LEFT JOIN steering_types st ON c.id_steering = st.id
            LEFT JOIN fuel_types ft ON c.id_fuel_type = ft.id
            LEFT JOIN transmissions tr ON c.id_transmission = tr.id
            LEFT JOIN drives d ON c.id_drive = d.id
            LEFT JOIN conditions cond ON c.id_condition = cond.id
        """
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY c.quantity DESC, c.brand ASC"

        rows = self.conn.execute(query, params).fetchall()
        self.cars = {}
        for row in rows:
            car_id, brand, model, year, price, stock = row
            stock_text = f"Р’ РЅР°Р»РёС‡РёРё: {stock} С€С‚." if stock > 0 else "РќРµС‚ РІ РЅР°Р»РёС‡РёРё"
            label = f"{brand} {model} ({year}) вЂ” {price:,.0f} СЂСѓР±. [{stock_text}]"
            self.cars[label] = car_id
        self.car_combo['values'] = list(self.cars.keys())
        self.car_count_label.config(text=f"РќР°Р№РґРµРЅРѕ Р°РІС‚РѕРјРѕР±РёР»РµР№: {len(self.cars)}")
        if self.cars:
            self.car_combo.current(0)
            self._on_car_selected()
        else:
            self.car_combo.set('')
            self._update_car_info_display(None)
            self.lbl_stock_status.config(text="")

    def _on_car_selected(self, event=None):
        selected = self.car_var.get()
        if selected not in self.cars:
            self._update_car_info_display(None)
            self.lbl_stock_status.config(text="")
            return
        car_id = self.cars[selected]
        info = get_car_info(self.conn, car_id)
        self._update_car_info_display(info)
        if info:
            if info['in_stock']:
                self.lbl_stock_status.config(text="вњ” Р’ РЅР°Р»РёС‡РёРё", style='Green.TLabel')
            else:
                self.lbl_stock_status.config(text="вњ РќРµС‚ РІ РЅР°Р»РёС‡РёРё", style='Red.TLabel')
        else:
            self.lbl_stock_status.config(text="")

    def _update_car_info_display(self, info):
        """РћР±РЅРѕРІР»СЏРµС‚ С‚РµРєСЃС‚РѕРІРѕРµ РїРѕР»Рµ СЃ РёРЅС„РѕСЂРјР°С†РёРµР№ РѕР± Р°РІС‚РѕРјРѕР±РёР»Рµ."""
        self.lbl_car_info.config(state='normal')
        self.lbl_car_info.delete(1.0, tk.END)
        if info:
            lines = [
                f"РњР°СЂРєР°/РњРѕРґРµР»СЊ: {info['description']}",
                f"Р“РѕРґ: {info['year']}, Р¦РІРµС‚: {info['color']}, Р¦РµРЅР°: {info['price']:,.0f} СЂСѓР±.",
                f"Р СѓР»СЊ: {info['steering']}, РњРѕС‰РЅРѕСЃС‚СЊ: {info['power']} Р».СЃ., РћР±СЉС‘Рј: {info['engine_volume']} Р»",
                f"РўРѕРїР»РёРІРѕ: {info['fuel_type']}, РљРџРџ: {info['transmission']}, РџСЂРёРІРѕРґ: {info['drive']}",
                f"РЎРѕСЃС‚РѕСЏРЅРёРµ: {info['condition']}" + (f", РџСЂРѕР±РµРі: {info['mileage']} РєРј" if info['mileage'] else ""),
            ]
            self.lbl_car_info.insert(tk.END, "\n".join(lines))
        else:
            self.lbl_car_info.insert(tk.END, "РђРІС‚РѕРјРѕР±РёР»СЊ РЅРµ РІС‹Р±СЂР°РЅ")
        self.lbl_car_info.config(state='disabled')

    def add_to_cart(self):
        if not self.cars:
            messagebox.showerror("РћС€РёР±РєР°", "РќРµС‚ РґРѕСЃС‚СѓРїРЅС‹С… Р°РІС‚РѕРјРѕР±РёР»РµР№ РІ РєР°С‚РµРіРѕСЂРёРё.")
            return
        selected = self.car_var.get()
        if selected not in self.cars:
            messagebox.showerror("РћС€РёР±РєР°", "Р’С‹Р±РµСЂРёС‚Рµ Р°РІС‚РѕРјРѕР±РёР»СЊ.")
            return
        try:
            qty = int(self.qty_entry.get())
            if qty <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("РћС€РёР±РєР°", "РљРѕР»РёС‡РµСЃС‚РІРѕ РґРѕР»Р¶РЅРѕ Р±С‹С‚СЊ С†РµР»С‹Рј РїРѕР»РѕР¶РёС‚РµР»СЊРЅС‹Рј С‡РёСЃР»РѕРј.")
            return

        car_id = self.cars[selected]
        info = get_car_info(self.conn, car_id)
        if not info:
            return

        self.cart.append({
            'car_id': car_id,
            'description': info['description'],
            'quantity': qty,
            'price_at_sale': info['price'],
            'in_stock': info['in_stock']
        })
        self.update_cart_display()
        self.qty_entry.delete(0, tk.END)
        self.qty_entry.insert(0, "1")

    def update_cart_display(self):
        self.cart_listbox.delete(0, tk.END)
        grouped = defaultdict(lambda: {'desc': '', 'qty': 0, 'price': 0.0, 'in_stock': True})
        for item in self.cart:
            g = grouped[item['car_id']]
            g['desc'] = item['description']
            g['qty'] += item['quantity']
            g['price'] = item['price_at_sale']
            g['in_stock'] = g['in_stock'] and item['in_stock']

        total = 0.0
        for g in grouped.values():
            subtotal = g['qty'] * g['price']
            status = "вњ”" if g['in_stock'] else "вњ (РїСЂРµРґР·Р°РєР°Р·)"
            self.cart_listbox.insert(tk.END,
                f"{status} {g['desc']}  Г— {g['qty']} = {subtotal:,.2f} СЂСѓР±.")
            total += subtotal
        self.cart_listbox.insert(tk.END, f"--- РРўРћР“Рћ: {total:,.2f} СЂСѓР±. ---")

    def remove_selected(self):
        sel = self.cart_listbox.curselection()
        if sel and sel[0] < len(self.cart):
            del self.cart[sel[0]]
            self.update_cart_display()

    def clear_cart(self):
        self.cart.clear()
        self.update_cart_display()

    def finalize_purchase(self):
        if not getattr(self, 'current_emp_id', None):
            messagebox.showerror("РћС€РёР±РєР°", "Р’С‹Р±РµСЂРёС‚Рµ РјРµРЅРµРґР¶РµСЂР°.")
            return
        cust_key = self.cust_var.get()
        if not cust_key or cust_key not in self.cust_map:
            messagebox.showerror("РћС€РёР±РєР°", "Р’С‹Р±РµСЂРёС‚Рµ РєР»РёРµРЅС‚Р° РёР· СЃРїРёСЃРєР°.")
            return
        customer_id = self.cust_map[cust_key]
        if not self.cart:
            messagebox.showerror("РћС€РёР±РєР°", "РљРѕСЂР·РёРЅР° РїСѓСЃС‚Р°.")
            return

        ok, msg = finalize_sale(self.conn, self.cart, self.current_emp_id, customer_id)
        if ok:
            messagebox.showinfo("РЈСЃРїРµС…", f"Р—Р°РєР°Р· в„–{msg} РѕС„РѕСЂРјР»РµРЅ. РЎРїР°СЃРёР±Рѕ!")
            self.cart.clear()
        else:
            messagebox.showerror("РћС€РёР±РєР°", msg)
        self.update_cart_display()
        self.refresh_categories()
        self.refresh_history_table()

    def load_cars_from_csv(self):
        filepath = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if not filepath:
            return
        cur = self.conn.cursor()
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    brand = row.get('brand', '').strip()
                    model = row.get('model', '').strip()
                    if not brand or not model:
                        continue
                    try:
                        year = int(row['year'])
                        color = row.get('color', '').strip()
                        vin = row['vin'].strip()
                        price = float(row['price'])
                        qty = int(row['quantity'])
                        cat_name = row['category'].strip()
                        steering_text = row.get('steering', 'left').strip().lower()
                        power = int(row['power'])
                        engine_volume = float(row['engine_volume']) if row.get('engine_volume') else None
                        fuel_text = row.get('fuel_type', '').strip().lower()
                        trans_text = row.get('transmission', '').strip().lower()
                        drive_text = row.get('drive', '').strip().lower()
                        cond_text = row.get('condition', 'new').strip().lower()
                        mileage = int(row['mileage']) if row.get('mileage') and row['mileage'].strip() else None
                    except (KeyError, ValueError) as e:
                        continue

                    # РџРѕР»СѓС‡Р°РµРј id РєР°С‚РµРіРѕСЂРёРё
                    cat_row = cur.execute("SELECT id FROM car_categories WHERE name = ?", (cat_name,)).fetchone()
                    if cat_row:
                        cat_id = cat_row[0]
                    else:
                        cur.execute("INSERT INTO car_categories (name) VALUES (?)", (cat_name,))
                        cat_id = cur.lastrowid

                    # Р¤СѓРЅРєС†РёСЏ РґР»СЏ РїРѕР»СѓС‡РµРЅРёСЏ id РёР· СЃРїСЂР°РІРѕС‡РЅРёРєР°
                    def get_ref_id(table, name):
                        if not name:
                            return None
                        r = cur.execute(f"SELECT id FROM {table} WHERE name = ?", (name,)).fetchone()
                        if r:
                            return r[0]
                        # Р•СЃР»Рё РЅРµС‚ вЂ“ РІСЃС‚Р°РІР»СЏРµРј (С…РѕС‚СЏ РѕР±С‹С‡РЅРѕ СЃРїСЂР°РІРѕС‡РЅРёРєРё СѓР¶Рµ Р·Р°РїРѕР»РЅРµРЅС‹)
                        cur.execute(f"INSERT INTO {table} (name) VALUES (?)", (name,))
                        return cur.lastrowid

                    id_steering = get_ref_id('steering_types', steering_text)
                    id_fuel = get_ref_id('fuel_types', fuel_text) if fuel_text else None
                    id_trans = get_ref_id('transmissions', trans_text) if trans_text else None
                    id_drive = get_ref_id('drives', drive_text) if drive_text else None
                    id_cond = get_ref_id('conditions', cond_text)

                    exist = cur.execute("SELECT id, quantity FROM cars WHERE vin = ?", (vin,)).fetchone()
                    if exist:
                        cur.execute("""
                            UPDATE cars SET price=?, quantity=quantity+?, id_category=?, id_steering=?,
                            power=?, engine_volume=?, id_fuel_type=?, id_transmission=?, id_drive=?,
                            id_condition=?, mileage=? WHERE id=?
                        """, (price, qty, cat_id, id_steering, power, engine_volume,
                            id_fuel, id_trans, id_drive, id_cond, mileage, exist[0]))
                    else:
                        cur.execute("""
                            INSERT INTO cars (brand, model, year, color, vin, price, quantity, id_category,
                            id_steering, power, engine_volume, id_fuel_type, id_transmission, id_drive, id_condition, mileage)
                            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                        """, (brand, model, year, color, vin, price, qty, cat_id,
                            id_steering, power, engine_volume, id_fuel, id_trans, id_drive, id_cond, mileage))
            self.conn.commit()
            messagebox.showinfo("РЈСЃРїРµС…", "РђРІС‚РѕРјРѕР±РёР»Рё Р·Р°РіСЂСѓР¶РµРЅС‹ РёР· CSV.")
            self.refresh_categories()
        except Exception as e:
            messagebox.showerror("РћС€РёР±РєР°", f"РћС€РёР±РєР° Р·Р°РіСЂСѓР·РєРё:\n{e}")

    def _display_report(self, date_str):
        if not date_str:
            messagebox.showerror("РћС€РёР±РєР°", "Р’РІРµРґРёС‚Рµ РґР°С‚Сѓ РІ С„РѕСЂРјР°С‚Рµ Р“Р“Р“Р“-РњРњ-Р”Р”")
            return
        data = get_report(self.conn, date_str)
        self.text_area.delete(1.0, tk.END)
        if not data:
            self.text_area.insert(tk.END, f"Р—Р° {date_str} Р·Р°РєР°Р·РѕРІ РЅРµС‚.")
            return
        total = sum(rev for _, _, rev in data)
        lines = [f"РћС‚С‡С‘С‚ Р·Р° {date_str}:\n"]
        lines += [f"{desc}: {qty} С€С‚. в†’ {rev:,.2f} СЂСѓР±." for desc, qty, rev in data]
        lines += [f"\nРС‚РѕРіРѕ РІС‹СЂСѓС‡РєР°: {total:,.2f} СЂСѓР±."]
        self.text_area.insert(tk.END, "\n".join(lines))

    def __del__(self):
        if hasattr(self, 'conn'):
            self.conn.close()

if __name__ == "__main__":
    root = tk.Tk()
    app = AutoDealerApp(root)
    root.mainloop()
