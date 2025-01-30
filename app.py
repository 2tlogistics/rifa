from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for
import base64
import json
import xlsxwriter
import io
import tempfile
import os
from datetime import datetime

app = Flask(__name__)

# Cargar datos de las rifas desde el archivo JSON
def load_raffles():
    try:
        with open('raffles.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

raffles = load_raffles()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/results')
def results():
    return render_template('results.html', raffles=raffles)

@app.route('/comprobantes')
def comprobantes():
    return render_template('comprobantes.html', raffles=raffles)

@app.route('/sorteo')
def sorteo():
    return render_template('sorteo.html', raffles=raffles)

@app.route('/reset')
def reset():
    return render_template('reset.html')

@app.route('/backup_and_reset', methods=['POST'])
def backup_and_reset():
    # Crear un backup del archivo raffles.json
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    backup_filename = f"bck_{timestamp}_raffles.json"
    with open('raffles.json', 'r') as original_file:
        data = original_file.read()
        with open(backup_filename, 'w') as backup_file:
            backup_file.write(data)
    
    # Borrar los datos del archivo original raffles.json
    with open('raffles.json', 'w') as original_file:
        original_file.write('[]')
    
    return redirect(url_for('index'))

@app.route('/menu')
def menu():
    return render_template('menu.html')

@app.route('/check_numbers', methods=['POST'])
def check_numbers():
    chosen_numbers = request.json['chosen_numbers']
    existing_numbers = [num for raffle in raffles for num in raffle['chosen_numbers']]
    
    for num in chosen_numbers:
        if num in existing_numbers:
            return jsonify({"error": f"El número {num} ya ha sido escogido. Por favor seleccione otro número."}), 400
    
    return jsonify({"success": "Números disponibles"}), 200

@app.route('/submit', methods=['POST'])
def submit():
    name = request.form['name']
    id_number = request.form['id_number']
    phone = request.form['phone']
    chosen_numbers = request.form.getlist('chosen_numbers')
    image = request.files['image']
    
    image_b64 = base64.b64encode(image.read()).decode('utf-8')
    
    # Generar número de ticket único
    ticket_number = f"{id_number[:2]}-{len(raffles)+1}"
    
    raffle_entry = {
        "name": name,
        "id_number": id_number,
        "phone": phone,
        "chosen_numbers": chosen_numbers,
        "image_b64": image_b64,
        "ticket_number": ticket_number
    }
    
    raffles.append(raffle_entry)
    
    with open('raffles.json', 'w') as f:
        json.dump(raffles, f)
    
    return jsonify({"success": "Rifa registrada", "ticket_number": ticket_number}), 200

@app.route('/export_results')
def export_results():
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet()

    # Escribir encabezados
    headers = ['Nombre', 'Cédula', 'Teléfono', 'Números Escogidos', 'Ticket']
    for col_num, header in enumerate(headers):
        worksheet.write(0, col_num, header)

    # Escribir datos
    for row_num, raffle in enumerate(raffles, start=1):
        worksheet.write(row_num, 0, raffle['name'])
        worksheet.write(row_num, 1, raffle['id_number'])
        worksheet.write(row_num, 2, raffle['phone'])
        worksheet.write(row_num, 3, ', '.join(raffle['chosen_numbers']))
        worksheet.write(row_num, 4, raffle['ticket_number'])

    workbook.close()
    output.seek(0)

    return send_file(output, as_attachment=True, download_name='Resultados_Rifas.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@app.route('/export_comprobantes')
def export_comprobantes():
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet()

    # Escribir encabezados
    headers = ['Ticket', 'Cédula', 'Imagen']
    for col_num, header in enumerate(headers):
        worksheet.write(0, col_num, header)

    # Escribir datos e insertar imágenes
    for row_num, raffle in enumerate(raffles, start=1):
        worksheet.write(row_num, 0, raffle['ticket_number'])
        worksheet.write(row_num, 1, raffle['id_number'])
        
        image_data = base64.b64decode(raffle['image_b64'])
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as img_file:
            img_file.write(image_data)
            image_path = img_file.name
        
        worksheet.insert_image(row_num, 2, image_path)
        os.remove(image_path)  # Eliminar archivo temporal después de insertar la imagen

    workbook.close()
    output.seek(0)

    return send_file(output, as_attachment=True, download_name='Comprobantes_Rifas.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

if __name__ == '__main__':
    app.run()
