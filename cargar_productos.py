import sqlite3

conn = sqlite3.connect("ferreteria.db")
cursor = conn.cursor()

# Crear tablas si no existen
cursor.execute("""
CREATE TABLE IF NOT EXISTS productos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS precios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    producto_id INTEGER,
    proveedor TEXT,
    precio INTEGER
)
""")

# -------- AGREGAR PRODUCTOS --------

productos = [
    ("Perfil Metalcon 90mm", "Proveedor A", 1500),
    ("Tornillo 6x1 1/4", "Proveedor B", 50),
    ("Plancha OSB 11mm", "Proveedor C", 8900),
]

for nombre, proveedor, precio in productos:
    cursor.execute("INSERT INTO productos (nombre) VALUES (?)", (nombre,))
    producto_id = cursor.lastrowid

    cursor.execute("""
    INSERT INTO precios (producto_id, proveedor, precio)
    VALUES (?, ?, ?)
    """, (producto_id, proveedor, precio))

conn.commit()
conn.close()

print("Productos cargados correctamente")