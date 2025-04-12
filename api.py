from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
from datetime import datetime, time, timedelta
import pytz
import os

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Database configuration
DB_PATH = "registro_qr.db"

def init_db():
    """Initialize the database with required tables if they don't exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create usuarios_permitidos table (allowed users)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS usuarios_permitidos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        apellido TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        activo BOOLEAN DEFAULT 1
    )
    ''')
    
    # Create registros table (attendance logs)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS registros (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT NOT NULL,
        hora TEXT NOT NULL,
        dia TEXT NOT NULL,
        nombre TEXT NOT NULL,
        apellido TEXT NOT NULL,
        email TEXT NOT NULL,
        timestamp INTEGER DEFAULT (strftime('%s', 'now'))
    )
    ''')
    
    # Create horarios_asignados table (assigned schedules)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS horarios_asignados (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER NOT NULL,
        dia TEXT NOT NULL,
        hora_entrada TEXT NOT NULL,
        hora_salida TEXT NOT NULL,
        FOREIGN KEY (usuario_id) REFERENCES usuarios_permitidos (id)
    )
    ''')
    
    # Insert sample data if the tables are empty
    
# Initialize the database on startup
init_db()

@app.route('/registrar_qr', methods=['POST'])
def registrar_qr():
    """
    Register a QR code scan, validating the user and creating attendance record
    """
    try:
        data = request.json
        
        # Extract user data from request
        nombre = data.get('name', '')
        apellido = data.get('surname', '')
        email = data.get('email', '')
        
        if not (nombre and apellido and email):
            return jsonify({"success": False, "message": "Datos incompletos"}), 400
        
        # Check if user is authorized
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT id FROM usuarios_permitidos WHERE email = ? AND activo = 1",
            (email,)
        )
        user_result = cursor.fetchone()
        
        if not user_result:
            conn.close()
            return jsonify({"success": False, "message": "Usuario no autorizado"}), 403
        
        user_id = user_result[0]
        
        # Get current date and time
        now = datetime.now()
        fecha = now.strftime("%Y-%m-%d")
        hora = now.strftime("%H:%M:%S")
        dia = now.strftime("%A")  # Day of week in English
        
        # Insert attendance record
        cursor.execute('''
            INSERT INTO registros (fecha, hora, dia, nombre, apellido, email)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (fecha, hora, dia, nombre, apellido, email))
        
        conn.commit()
        registro_id = cursor.lastrowid
        conn.close()
        
        # Determine if this is entry or exit
        tipo = determinar_tipo_registro(email)
        
        return jsonify({
            "success": True,
            "message": f"Registro exitoso: {nombre} {apellido}",
            "id": registro_id,
            "fecha": fecha,
            "hora": hora,
            "tipo": tipo
        }), 201
        
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500

def determinar_tipo_registro(email):
    """
    Determine if this registration is an entry or exit based on previous records
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get current date
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Count today's records for this user
    cursor.execute('''
        SELECT COUNT(*) FROM registros 
        WHERE email = ? AND fecha = ?
    ''', (email, today))
    
    count = cursor.fetchone()[0]
    conn.close()
    
    # Even counts (including 0) are entries, odd counts are exits
    return "Entrada" if count % 2 == 0 else "Salida"

@app.route('/registros_hoy', methods=['GET'])
def registros_hoy():
    """
    Get all attendance records for today
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get current date
        today = datetime.now().strftime("%Y-%m-%d")
        
        cursor.execute('''
            SELECT id, fecha, hora, nombre, apellido, email
            FROM registros
            WHERE fecha = ?
            ORDER BY timestamp ASC
        ''', (today,))
        
        registros = []
        for row in cursor.fetchall():
            id, fecha, hora, nombre, apellido, email = row
            registros.append({
                "id": id,
                "fecha": fecha,
                "hora": hora,
                "nombre": nombre,
                "apellido": apellido,
                "email": email
            })
        
        conn.close()
        return jsonify(registros), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/cumplimiento', methods=['GET'])
def cumplimiento():
    """
    Get compliance data for users today
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get current date and time
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        dia_semana = now.strftime("%A")  # Day of week
        hora_actual = now.strftime("%H:%M:%S")
        
        # Get all authorized users
        cursor.execute("SELECT id, nombre, apellido, email FROM usuarios_permitidos WHERE activo = 1")
        usuarios = cursor.fetchall()
        
        resultado = []
        for user_id, nombre, apellido, email in usuarios:
            # Get scheduled blocks for this user today
            cursor.execute("""
                SELECT hora_entrada, hora_salida 
                FROM horarios_asignados
                WHERE usuario_id = ? AND dia = ?
                ORDER BY hora_entrada
            """, (user_id, dia_semana))
            
            bloques_horario = cursor.fetchall()
            
            # Get attendance records for this user TODAY ONLY
            cursor.execute("""
                SELECT hora
                FROM registros
                WHERE email = ? AND fecha = ?
                ORDER BY hora
            """, (email, today))
            
            registros_hoy = cursor.fetchall()
            hora_registros = [reg[0] for reg in registros_hoy]
            
            # Process user's compliance
            bloques_estado = []
            estado_general = "No Aplica"  # Default to No Aplica instead of Ausente
            
            # If they have a schedule for today
            if bloques_horario:
                estado_general = "Ausente"  # Reset to Ausente if they have a schedule
                
                for hora_entrada, hora_salida in bloques_horario:
                    estado_bloque = evaluar_bloque(hora_entrada, hora_salida, hora_actual, hora_registros, today)
                    bloques_estado.append({
                        "inicio": hora_entrada,
                        "fin": hora_salida,
                        "estado": estado_bloque
                    })
                    
                    # Update general state based on blocks
                    if estado_bloque == "Cumpliendo" and estado_general != "Cumpliendo":
                        estado_general = "Cumpliendo"
                    elif estado_bloque == "Incompleto" and estado_general == "Ausente":
                        estado_general = "Incompleto"
                    elif estado_bloque == "Retrasado" and estado_general == "Ausente":
                        estado_general = "Retrasado"
            
            resultado.append({
                "nombre": nombre,
                "apellido": apellido,
                "email": email,
                "estado": estado_general,
                "bloques": bloques_estado
            })
        
        conn.close()
        return jsonify(resultado), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def evaluar_bloque(hora_entrada, hora_salida, hora_actual, registros, fecha_actual=None):
    """
    Evaluate a time block's compliance status
    """
    # Convert string times to datetime.time objects for comparison
    entrada_time = datetime.strptime(hora_entrada, "%H:%M:%S").time()
    salida_time = datetime.strptime(hora_salida, "%H:%M:%S").time()
    actual_time = datetime.strptime(hora_actual, "%H:%M:%S").time()
    
    # Convert registration times
    registros_time = [datetime.strptime(reg, "%H:%M:%S").time() for reg in registros]
    
    # Check if this block is in the future
    if entrada_time > actual_time:
        return "Pendiente"
    
    # Check if this block is in the past
    if salida_time < actual_time:
        # Check if we have at least two registrations within this block
        entradas_en_bloque = [reg for reg in registros_time if entrada_time <= reg <= salida_time]
        
        if len(entradas_en_bloque) >= 2:
            return "Cumplido"
        elif len(entradas_en_bloque) == 1:
            return "Incompleto"
        else:
            return "Ausente"
    
    # Current block (in progress)
    entradas_en_bloque = [reg for reg in registros_time if entrada_time <= reg <= actual_time]
    
    if len(entradas_en_bloque) >= 1:
        return "Cumpliendo"
    elif actual_time > entrada_time:
        # Current time is after block start but no registrations
        mins_late = (datetime.combine(datetime.today(), actual_time) - 
                    datetime.combine(datetime.today(), entrada_time)).total_seconds() / 60
        
        if mins_late > 15:
            return "Retrasado"
        else:
            return "Pendiente"  # Give a 15-min grace period
    else:
        return "Pendiente"

@app.route('/usuarios', methods=['GET'])
def get_usuarios():
    """
    Get list of all authorized users
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, nombre, apellido, email FROM usuarios_permitidos WHERE activo = 1")
        
        usuarios = []
        for row in cursor.fetchall():
            id, nombre, apellido, email = row
            usuarios.append({
                "id": id,
                "nombre": nombre,
                "apellido": apellido,
                "email": email
            })
        
        conn.close()
        return jsonify(usuarios), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/horarios', methods=['GET'])
def get_horarios():
    """
    Get schedules for all users or filtered by user ID
    """
    try:
        user_id = request.args.get('usuario_id')
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        if user_id:
            cursor.execute("""
                SELECT h.id, h.usuario_id, u.nombre, u.apellido, h.dia, h.hora_entrada, h.hora_salida
                FROM horarios_asignados h
                JOIN usuarios_permitidos u ON h.usuario_id = u.id
                WHERE h.usuario_id = ?
                ORDER BY h.dia, h.hora_entrada
            """, (user_id,))
        else:
            cursor.execute("""
                SELECT h.id, h.usuario_id, u.nombre, u.apellido, h.dia, h.hora_entrada, h.hora_salida
                FROM horarios_asignados h
                JOIN usuarios_permitidos u ON h.usuario_id = u.id
                ORDER BY u.nombre, h.dia, h.hora_entrada
            """)
        
        horarios = []
        for row in cursor.fetchall():
            id, usuario_id, nombre, apellido, dia, hora_entrada, hora_salida = row
            horarios.append({
                "id": id,
                "usuario_id": usuario_id,
                "nombre": nombre,
                "apellido": apellido,
                "dia": dia,
                "hora_entrada": hora_entrada,
                "hora_salida": hora_salida
            })
        
        conn.close()
        return jsonify(horarios), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/historico', methods=['GET'])
def get_historico():
    """
    Get historical attendance records filtered by date range
    """
    try:
        fecha_inicio = request.args.get('fecha_inicio', datetime.now().strftime("%Y-%m-01"))
        fecha_fin = request.args.get('fecha_fin', datetime.now().strftime("%Y-%m-%d"))
        email = request.args.get('email')
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        query = """
            SELECT id, fecha, hora, dia, nombre, apellido, email
            FROM registros
            WHERE fecha BETWEEN ? AND ?
        """
        params = [fecha_inicio, fecha_fin]
        
        if email:
            query += " AND email = ?"
            params.append(email)
        
        query += " ORDER BY fecha DESC, hora ASC"
        
        cursor.execute(query, params)
        
        registros = []
        for row in cursor.fetchall():
            id, fecha, hora, dia, nombre, apellido, email = row
            registros.append({
                "id": id,
                "fecha": fecha,
                "hora": hora,
                "dia": dia,
                "nombre": nombre,
                "apellido": apellido,
                "email": email
            })
        
        conn.close()
        return jsonify(registros), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/resumen', methods=['GET'])
def get_resumen():
    """
    Get summary of attendance statistics for the current month
    """
    try:
        # Get current month
        now = datetime.now()
        year_month = now.strftime("%Y-%m")
        fecha_inicio = f"{year_month}-01"
        
        # Calculate last day of the month
        if now.month == 12:
            next_month = datetime(now.year + 1, 1, 1)
        else:
            next_month = datetime(now.year, now.month + 1, 1)
        
        last_day = (next_month - timedelta(days=1)).day
        fecha_fin = f"{year_month}-{last_day}"
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get all users
        cursor.execute("SELECT id, nombre, apellido, email FROM usuarios_permitidos WHERE activo = 1")
        usuarios = cursor.fetchall()
        
        resultado = []
        for user_id, nombre, apellido, email in usuarios:
            # Count days with complete attendance
            cursor.execute("""
                SELECT fecha, COUNT(*) as registros
                FROM registros
                WHERE email = ? AND fecha BETWEEN ? AND ?
                GROUP BY fecha
                HAVING COUNT(*) >= 2
            """, (email, fecha_inicio, fecha_fin))
            
            dias_completos = len(cursor.fetchall())
            
            # Count days with incomplete attendance
            cursor.execute("""
                SELECT fecha, COUNT(*) as registros
                FROM registros
                WHERE email = ? AND fecha BETWEEN ? AND ?
                GROUP BY fecha
                HAVING COUNT(*) = 1
            """, (email, fecha_inicio, fecha_fin))
            
            dias_incompletos = len(cursor.fetchall())
            
            # Get scheduled days for this month
            cursor.execute("""
                SELECT DISTINCT dia
                FROM horarios_asignados
                WHERE usuario_id = ?
            """, (user_id,))
            
            dias_programados = set([row[0] for row in cursor.fetchall()])
            
            # Count working days in this month
            dias_habiles = 0
            fecha_actual = datetime.strptime(fecha_inicio, "%Y-%m-%d")
            fecha_final = datetime.strptime(fecha_fin, "%Y-%m-%d")
            
            while fecha_actual <= fecha_final:
                if fecha_actual.strftime("%A") in dias_programados:
                    dias_habiles += 1
                fecha_actual += timedelta(days=1)
            
            # Calculate compliance percentage
            cumplimiento = (dias_completos / dias_habiles * 100) if dias_habiles > 0 else 0
            
            resultado.append({
                "nombre": nombre,
                "apellido": apellido,
                "email": email,
                "dias_completos": dias_completos,
                "dias_incompletos": dias_incompletos,
                "dias_habiles": dias_habiles,
                "cumplimiento": round(cumplimiento, 2)
            })
        
        conn.close()
        return jsonify(resultado), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/horas_acumuladas', methods=['GET'])
def get_horas_acumuladas():
    """
    Get accumulated hours for each user historically
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get all users
        cursor.execute("SELECT id, nombre, apellido, email FROM usuarios_permitidos WHERE activo = 1")
        usuarios = cursor.fetchall()
        
        resultado = []
        for user_id, nombre, apellido, email in usuarios:
            # Get all attendance records for this user
            cursor.execute("""
                SELECT fecha, hora, id
                FROM registros
                WHERE email = ?
                ORDER BY fecha, hora
            """, (email,))
            
            registros = cursor.fetchall()
            total_minutos = 0
            horas_por_fecha = {}
            
            # Process records in pairs (entry/exit)
            fecha_actual = None
            registros_del_dia = []
            
            for fecha, hora, reg_id in registros:
                if fecha != fecha_actual:
                    # Process previous day's records
                    if fecha_actual and registros_del_dia:
                        minutos_dia, registro_detalle = calcular_horas_del_dia(registros_del_dia)
                        total_minutos += minutos_dia
                        horas_por_fecha[fecha_actual] = {
                            "minutos": minutos_dia,
                            "horas": round(minutos_dia / 60, 2),
                            "detalle": registro_detalle
                        }
                    
                    # Reset for new day
                    fecha_actual = fecha
                    registros_del_dia = []
                
                registros_del_dia.append((hora, reg_id))
            
            # Process last day's records
            if fecha_actual and registros_del_dia:
                minutos_dia, registro_detalle = calcular_horas_del_dia(registros_del_dia)
                total_minutos += minutos_dia
                horas_por_fecha[fecha_actual] = {
                    "minutos": minutos_dia,
                    "horas": round(minutos_dia / 60, 2),
                    "detalle": registro_detalle
                }
            
            # Add user's total
            resultado.append({
                "nombre": nombre,
                "apellido": apellido,
                "email": email,
                "horas_totales": round(total_minutos / 60, 2),
                "minutos_totales": total_minutos,
                "detalle_por_fecha": horas_por_fecha
            })
        
        conn.close()
        return jsonify(resultado), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def calcular_horas_del_dia(registros_del_dia):
    """
    Calculates the number of minutes worked in a day from a list of time records
    """
    minutos_totales = 0
    registro_detalle = []
    
    # Process records in pairs (entry/exit)
    for i in range(0, len(registros_del_dia) - 1, 2):
        if i + 1 < len(registros_del_dia):
            hora_entrada = registros_del_dia[i][0]
            hora_salida = registros_del_dia[i + 1][0]
            
            # Convert to datetime objects
            entrada_dt = datetime.strptime(hora_entrada, "%H:%M:%S")
            salida_dt = datetime.strptime(hora_salida, "%H:%M:%S")
            
            # Calculate difference in minutes
            diff_minutes = (salida_dt - entrada_dt).total_seconds() / 60
            
            # Only add positive differences
            if diff_minutes > 0:
                minutos_totales += diff_minutes
                registro_detalle.append({
                    "entrada": hora_entrada,
                    "salida": hora_salida,
                    "minutos": round(diff_minutes, 2)
                })
    
    return minutos_totales, registro_detalle

@app.route('/admin/usuario', methods=['POST'])
def add_usuario():
    """
    Add a new authorized user
    """
    try:
        data = request.json
        nombre = data.get('nombre')
        apellido = data.get('apellido')
        email = data.get('email')
        
        if not (nombre and apellido and email):
            return jsonify({"success": False, "message": "Datos incompletos"}), 400
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if email already exists
        cursor.execute("SELECT id FROM usuarios_permitidos WHERE email = ?", (email,))
        if cursor.fetchone():
            conn.close()
            return jsonify({"success": False, "message": "Email ya registrado"}), 409
        
        # Insert new user
        cursor.execute("""
            INSERT INTO usuarios_permitidos (nombre, apellido, email)
            VALUES (?, ?, ?)
        """, (nombre, apellido, email))
        
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        
        return jsonify({
            "success": True,
            "message": "Usuario agregado correctamente",
            "id": new_id
        }), 201
        
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500

@app.route('/admin/horario', methods=['POST'])
def add_horario():
    """
    Add a schedule block for a user
    """
    try:
        data = request.json
        usuario_id = data.get('usuario_id')
        dia = data.get('dia')
        hora_entrada = data.get('hora_entrada')
        hora_salida = data.get('hora_salida')
        
        if not (usuario_id and dia and hora_entrada and hora_salida):
            return jsonify({"success": False, "message": "Datos incompletos"}), 400
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute("SELECT id FROM usuarios_permitidos WHERE id = ?", (usuario_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({"success": False, "message": "Usuario no encontrado"}), 404
        
        # Insert schedule block
        cursor.execute("""
            INSERT INTO horarios_asignados (usuario_id, dia, hora_entrada, hora_salida)
            VALUES (?, ?, ?, ?)
        """, (usuario_id, dia, hora_entrada, hora_salida))
        
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        
        return jsonify({
            "success": True,
            "message": "Horario agregado correctamente",
            "id": new_id
        }), 201
        
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)