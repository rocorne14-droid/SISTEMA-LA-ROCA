import sqlite3

conn = sqlite3.connect("ferreteria.db")
cursor = conn.cursor()

# Tabla productos
cursor.execute("""
CREATE TABLE IF NOT EXISTS productos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT UNIQUE
)
""")

# Tabla precios
cursor.execute("""
CREATE TABLE IF NOT EXISTS precios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    producto_id INTEGER,
    proveedor TEXT,
    precio INTEGER,
    FOREIGN KEY(producto_id) REFERENCES productos(id)
)
""")

conn.commit()
conn.close()

print("Base de datos creada correctamente")