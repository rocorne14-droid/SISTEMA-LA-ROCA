from flask import Flask, render_template, request, redirect, session, send_file
import sqlite3
import pytesseract
from PIL import Image
import fitz  # PyMuPDF
import re
import os
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Image as RLImage, Spacer, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

app = Flask(__name__)
app.secret_key = "ferreteria_pro_2026_super_seguro"
MARGEN = 0.30  # 30%

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

# ---------------- PDF LECTOR ----------------
def leer_pdf(ruta):
    doc = fitz.open(ruta)
    texto = ""

    for page in doc:
        texto += page.get_text()

    return texto


def extraer_productos(texto):
    productos = []
    lineas = texto.split("\n")

    for l in lineas:
        match = re.search(r'(.+?)\s+(\d{1,3}(?:\.\d{3})*)$', l)

        if match:
            nombre = match.group(1).strip()
            precio = int(match.group(2).replace(".", ""))
            productos.append((nombre, precio))

    return productos


def guardar_productos(lista, proveedor="PDF"):
    conn = sqlite3.connect("ferreteria.db")
    cursor = conn.cursor()

    for nombre, precio in lista:
        cursor.execute("SELECT id FROM productos WHERE nombre = ?", (nombre,))
        existe = cursor.fetchone()

        if existe:
            producto_id = existe[0]
        else:
            cursor.execute("INSERT INTO productos (nombre) VALUES (?)", (nombre,))
            producto_id = cursor.lastrowid

        cursor.execute("""
        INSERT INTO precios (producto_id, proveedor, precio)
        VALUES (?, ?, ?)
        """, (producto_id, proveedor, precio))

    conn.commit()
    conn.close()

# ---------------- ROUTES ----------------

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/buscar", methods=["POST"])
def buscar():
    texto = request.form["producto"]
    resultados = buscar_producto(texto)

    cotizacion = session.get("cotizacion", [])
    vistos = {p[0] for p in cotizacion}

    for r in resultados:
        if r[0] not in vistos:
            cotizacion.append(r)
            vistos.add(r[0])

    session["cotizacion"] = cotizacion
    return redirect("/cotizacion")

@app.route("/set_margen", methods=["POST"])
def set_margen():
    margen = float(request.form["margen"])
    session["margen"] = margen
    return redirect("/cotizacion")

@app.route("/ocr", methods=["POST"])
def ocr():
    if "imagen" not in request.files:
        return "No se subió imagen"

    file = request.files["imagen"]

    if file.filename == "":
        return "Archivo vacío"

    ruta = "temp.png"
    file.save(ruta)

    texto = leer_imagen(ruta)
    os.remove(ruta)

    lineas = texto.split("\n")

    cotizacion = session.get("cotizacion", [])
    vistos = {p[0] for p in cotizacion}

    for l in lineas:
        if len(l.strip()) > 3:
            productos = buscar_producto(l)

            if productos:
                nombre = productos[0][0]

                if nombre not in vistos:
                    cotizacion.append(productos[0])
                    vistos.add(nombre)

    session["cotizacion"] = cotizacion
    return redirect("/cotizacion")

@app.route("/cotizacion")
def cotizacion():
    datos = session.get("cotizacion", [])
    margen = float(session.get("margen", 0.30))

    datos_con_margen = []
    total = 0
    total_costo = 0

    for p in datos:
        try:
            costo = float(p[2])
        except:
            continue

        venta = int(costo * (1 + margen))
        ganancia = venta - costo

        datos_con_margen.append((p[0], p[1], int(costo), venta, ganancia))

        total += venta
        total_costo += costo

    utilidad_total = total - total_costo

    return render_template(
        "cotizacion.html",
        datos=datos_con_margen,
        total=total,
        margen=margen,
        utilidad_total=int(utilidad_total)
    )

@app.route("/cargar_pdf", methods=["POST"])
def cargar_pdf():
    file = request.files["pdf"]
    ruta = "catalogo.pdf"
    file.save(ruta)

    texto = leer_pdf(ruta)
    productos = extraer_productos(texto)

    os.remove(ruta)
    guardar_productos(productos)

    return "PDF cargado correctamente"

@app.route("/pdf")
def pdf():
    datos = session.get("cotizacion", [])
    margen = float(session.get("margen", 0.30))

    archivo = "cotizacion.pdf"

    doc = SimpleDocTemplate(
        archivo,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=20
    )

    styles = getSampleStyleSheet()

    # LOGO
    if os.path.exists("static/logo.png"):
        logo = RLImage("static/logo.png", width=120, height=60)
    else:
        logo = Paragraph("FERRETERÍA LA ROCA SPA", styles["Title"])

    titulo = Paragraph("<b>FERRETERÍA LA ROCA SPA</b>", styles["Title"])

    info = Paragraph(
        "Dirección: Santiago, Chile<br/>"
        "Tel: +56 9 0000 0000<br/>"
        "Email: ventas@laroca.cl",
        styles["Normal"]
    )

    fecha = datetime.now().strftime("%d-%m-%Y %H:%M")
    numero = datetime.now().strftime("%Y%m%d%H%M")

    encabezado = Paragraph(
        f"<b>COTIZACIÓN Nº:</b> {numero}<br/>"
        f"<b>Fecha:</b> {fecha}",
        styles["Normal"]
    )

    # TABLA
    data = [["Producto", "Proveedor", "Costo", "Venta", "Ganancia"]]

    total = 0
    total_costo = 0

    for p in datos:
        try:
            costo = float(p[2])
        except:
            continue

        venta = int(costo * (1 + margen))
        ganancia = venta - costo

        data.append([
            p[0],
            p[1],
            f"${int(costo):,}".replace(",", "."),
            f"${int(venta):,}".replace(",", "."),
            f"${int(ganancia):,}".replace(",", ".")
        ])

        total += venta
        total_costo += costo

    utilidad = total - total_costo

    data.append(["", "", "", "", ""])
    data.append(["", "", "TOTAL COSTO", "", f"${int(total_costo):,}".replace(",", ".")])
    data.append(["", "", "TOTAL VENTA", "", f"${int(total):,}".replace(",", ".")])
    data.append(["", "", "UTILIDAD", "", f"${int(utilidad):,}".replace(",", ".")])

    tabla = Table(data)
    tabla.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('BACKGROUND', (0,0), (-1,0), colors.black),
        ('TEXTCOLOR',(0,0),(-1,0),colors.white),
    ]))

    pie = Paragraph(
        "Gracias por su preferencia.<br/>Esta cotización tiene validez de 5 días.",
        styles["Normal"]
    )

    elementos = [
        logo,
        Spacer(1, 10),
        titulo,
        info,
        Spacer(1, 10),
        encabezado,
        Spacer(1, 20),
        tabla,
        Spacer(1, 20),
        pie
    ]

    doc.build(elementos)

    return send_file(archivo, as_attachment=True)

@app.route("/eliminar/<nombre>")
def eliminar(nombre):
    cotizacion = session.get("cotizacion", [])
    nueva = [p for p in cotizacion if p[0] != nombre]
    session["cotizacion"] = nueva
    return redirect("/cotizacion")

@app.route("/limpiar")
def limpiar():
    session["cotizacion"] = []
    return redirect("/cotizacion")

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)