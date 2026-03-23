from flask import Flask, render_template, request, redirect, session, send_file
import sqlite3
import pytesseract
from PIL import Image
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors

app = Flask(__name__)
app.secret_key = "1234"

# ---------------- DB ----------------
def buscar_producto(texto):
    conn = sqlite3.connect("ferreteria.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT p.nombre, pr.proveedor, pr.precio
    FROM productos p
    JOIN precios pr ON p.id = pr.producto_id
    WHERE p.nombre LIKE ?
    ORDER BY pr.precio ASC
    """, ('%' + texto + '%',))

    data = cursor.fetchall()
    conn.close()
    return data

# ---------------- OCR ----------------
def leer_imagen(ruta):
    img = Image.open(ruta)
    return pytesseract.image_to_string(img)

# ---------------- ROUTES ----------------

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/ocr", methods=["POST"])
def ocr():
    file = request.files["imagen"]
    ruta = "temp.png"
    file.save(ruta)

    texto = leer_imagen(ruta)
    lineas = texto.split("\n")

    cotizacion = []

    for l in lineas:
        if len(l.strip()) > 3:
            productos = buscar_producto(l)
            if productos:
                cotizacion.append(productos[0])

    session["cotizacion"] = cotizacion
    return redirect("/cotizacion")

@app.route("/cotizacion")
def cotizacion():
    datos = session.get("cotizacion", [])
    total = sum(p[2] for p in datos)
    return render_template("cotizacion.html", datos=datos, total=total)

@app.route("/pdf")
def pdf():
    datos = session.get("cotizacion", [])

    archivo = "cotizacion.pdf"
    doc = SimpleDocTemplate(archivo)

    data = [["Producto", "Proveedor", "Precio"]]

    total = 0
    for p in datos:
        data.append([p[0], p[1], f"${p[2]}"])
        total += p[2]

    data.append(["TOTAL", "", f"${total}"])

    tabla = Table(data)
    tabla.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('BACKGROUND', (0,0), (-1,0), colors.black),
        ('TEXTCOLOR',(0,0),(-1,0),colors.white)
    ]))

    doc.build([tabla])

    return send_file(archivo, as_attachment=True)

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run()