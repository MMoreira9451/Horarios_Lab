import kivy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.clock import Clock
from kivy.graphics.texture import Texture
from kivy.uix.modalview import ModalView
from kivy.utils import get_color_from_hex
from kivy.core.window import Window
import cv2
from pyzbar.pyzbar import decode
import json
import time
from datetime import datetime
import sqlite3
import unicodedata

class LectorQR(BoxLayout):
    def __init__(self, **kwargs):
        super(LectorQR, self).__init__(**kwargs)
        self.orientation = 'vertical'
        
        # Configuración de la cámara
        self.capture = cv2.VideoCapture(0)
        self.capture.set(3, 640)  # Ancho
        self.capture.set(4, 480)  # Alto
        
        # Estado del lector
        self.is_scanning = True
        self.last_scan_time = 0
        self.scan_cooldown = 5  # Segundos entre escaneos
        
        # Configuración de la base de datos
        self.db_path = "registro_qr.db"
        
        # Crear la interfaz de usuario
        self.setup_ui()
        
        # Iniciar la actualización de la cámara
        Clock.schedule_interval(self.update, 1.0 / 30.0)  # 30 FPS
    
    def normalize_text(self, text):
        """Normaliza el texto para comparaciones"""
        if text is None:
            return ""

        # Ensure we're working with unicode strings
        if isinstance(text, bytes):
            try:
                text = text.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    text = text.decode('latin-1')
                except UnicodeDecodeError:
                    text = text.decode('utf-8', errors='ignore')

        # Clean up encoding artifacts without re-encoding
        text = text.replace('ﾃｭ', 'í')
        text = text.replace('ﾃｱ', 'ñ')
        text = text.replace('ﾃ³', 'ó')
        text = text.replace('ﾃ¡', 'á')
        text = text.replace('ﾃ©', 'é')
        text = text.replace('ﾃｺ', 'ú')

        # Then proceed with normalization
        text = text.lower()
    
        # Use unicodedata to remove accents but avoid re-encoding issues
        normalized = ''
        for c in unicodedata.normalize('NFD', text):
            if unicodedata.category(c) != 'Mn':
                normalized += c
    
        # Handle ñ specifically
        normalized = normalized.replace('ñ', 'n')
    
        # Remove non-alphanumeric characters
        normalized = ''.join(c for c in normalized if c.isalnum() or c.isspace())
    
        return normalized
    
    def setup_ui(self):
        # Título
        title_box = BoxLayout(size_hint=(1, 0.1))
        self.title_label = Label(
            text="Lector de QR", 
            font_size='24sp',
            color=get_color_from_hex('#FFFFFF')
        )
        title_box.add_widget(self.title_label)
        self.add_widget(title_box)
        
        # Vista de la cámara
        self.image = Image(size_hint=(1, 0.7))
        self.add_widget(self.image)
        
        # Área de estado
        status_box = BoxLayout(size_hint=(1, 0.1), padding=[10, 5])
        self.status_label = Label(
            text="Escanea un código QR",
            font_size='18sp',
            color=get_color_from_hex('#CCCCCC')
        )
        status_box.add_widget(self.status_label)
        self.add_widget(status_box)
        
        # Botones
        button_box = BoxLayout(size_hint=(1, 0.1), padding=[10, 5], spacing=10)
        
        self.toggle_button = Button(
            text="Pausar",
            background_color=get_color_from_hex('#5D9CEC'),
            color=get_color_from_hex('#FFFFFF'),
            size_hint=(0.5, 1)
        )
        self.toggle_button.bind(on_press=self.toggle_scanning)
        
        self.quit_button = Button(
            text="Salir",
            background_color=get_color_from_hex('#ED5565'),
            color=get_color_from_hex('#FFFFFF'),
            size_hint=(0.5, 1)
        )
        self.quit_button.bind(on_press=self.quit_app)
        
        button_box.add_widget(self.toggle_button)
        button_box.add_widget(self.quit_button)
        self.add_widget(button_box)
    
    def update(self, dt):
        # Capturar frame de la cámara
        ret, frame = self.capture.read()
        
        if ret:
            # Voltear horizontalmente para una vista de espejo
            frame = cv2.flip(frame, 1)
            
            # Procesar para encontrar códigos QR si el escáner está activo
            if self.is_scanning:
                # Convertir a escala de grises para mejor detección
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                qr_codes = decode(gray)
                
                current_time = time.time()
                
                for qr in qr_codes:
                    # Dibujar rectángulo alrededor del QR
                    points = qr.polygon
                    if points:
                        pts = []
                        for point in points:
                            pts.append([point.x, point.y])
                        
                        pts = np.array(pts, np.int32)
                        pts = pts.reshape((-1, 1, 2))
                        cv2.polylines(frame, [pts], True, (0, 255, 0), 3)
                    
                    # Procesar datos del QR si ha pasado suficiente tiempo desde el último escaneo
                    if current_time - self.last_scan_time > self.scan_cooldown:
                        data = qr.data.decode('utf-8')
                        self.verificar_usuario(data)
                        self.last_scan_time = current_time
            
            # Convertir para mostrar en Kivy
            buf = cv2.flip(frame, 0).tobytes()
            texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='bgr')
            texture.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
            self.image.texture = texture
    
    def verificar_usuario(self, data):
        try:
            # Add logging for raw data
            print(f"Raw QR data: {data}")
    
            try:
                # Try to decode with utf-8 first
                user_data = json.loads(data)
            
                # Log the parsed data
                print(f"Parsed QR data: {user_data}")
            
                # Clean up the string values to handle encoding issues
                for key in ['name', 'surname', 'email']:
                    if key in user_data:
                        # Clean up potential encoding issues
                        try:
                            cleaned_value = user_data[key].encode('utf-8').decode('utf-8')
                        except (UnicodeEncodeError, UnicodeDecodeError):
                                cleaned_value = user_data[key].encode('utf-8', errors='replace').decode('utf-8', errors='replace')

                        user_data[key] = cleaned_value.strip()
            
                # Log the cleaned data
                print(f"Cleaned QR data: {user_data}")
            
                # Rest of your code...
            
                # Verify if QR is expired
                if user_data.get('expired') == True or user_data.get('status') == "EXPIRED":
                    self.mostrar_resultado(False, "QR expirado", "El código QR ha expirado")
                    return
            
                # If we get here, verify the data with the local database
                self.status_label.text = "Verificando usuario..."
            
                # Extract user data
                nombre = user_data.get('name', '')
                apellido = user_data.get('surname', '')
                email = user_data.get('email', '')
            
                # Log the extracted data before normalization
                print(f"Before normalization - Nombre: {nombre}, Apellido: {apellido}, Email: {email}")
            
                # Verify user in database
                resultado = self.verificar_usuario_db(nombre, apellido, email)
            
                # Show result
                if resultado["success"]:
                    self.mostrar_resultado(True, "Registro exitoso", resultado["message"])
                else:
                    self.mostrar_resultado(False, "Error", resultado["error"])
            
            except json.JSONDecodeError:
                # If QR contains "Expirado" as plain text
                if "Expirado" in data:
                    self.mostrar_resultado(False, "QR expirado", "El código QR ha expirado")
                else:
                    self.mostrar_resultado(False, "Formato inválido", "El QR no tiene un formato JSON válido")
    
        except Exception as e:
            print(f"Error processing QR: {str(e)}")
            self.mostrar_resultado(False, "Error", f"Error al procesar el QR: {str(e)}")
    
    def verificar_usuario_db(self, nombre, apellido, email):
        try:
            # Connect to database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
    
            # Normalize user data from QR
            norm_nombre = self.normalize_text(nombre)
            norm_apellido = self.normalize_text(apellido)
            norm_email = self.normalize_text(email)
    
            # Add logs for debugging
            print(f"QR Data after normalization - Nombre: {norm_nombre}, Apellido: {norm_apellido}, Email: {norm_email}")
    
            # Check if user is allowed
            cursor.execute("SELECT id, nombre, apellido, email FROM usuarios_permitidos")
            all_permitted_users = cursor.fetchall()
    
            is_permitted = False
            matching_user = None
    
            for user in all_permitted_users:
                db_id, db_nombre, db_apellido, db_email = user
        
                # Normalize database data
                norm_db_nombre = self.normalize_text(db_nombre)
                norm_db_apellido = self.normalize_text(db_apellido)
                norm_db_email = self.normalize_text(db_email)
        
                # Print for debugging
                print(f"DB User - ID: {db_id}, Nombre: {norm_db_nombre}, Apellido: {norm_db_apellido}, Email: {norm_db_email}")
        
                # Email is the most reliable identifier, try that first
                if norm_db_email == norm_email:
                    is_permitted = True
                    matching_user = user
                    break
        
                # If email doesn't match exactly, try with name and surname
                elif (norm_db_nombre == norm_nombre and norm_db_apellido == norm_apellido):
                    is_permitted = True
                    matching_user = user
                    break
            
                # Even more relaxed matching - if both name and email partially match
                elif (norm_db_email.find(norm_email) != -1 or norm_email.find(norm_db_email) != -1) and \
                     (norm_db_nombre.find(norm_nombre) != -1 or norm_nombre.find(norm_db_nombre) != -1):
                    is_permitted = True
                    matching_user = user
                    break
    
            if not is_permitted:
                conn.close()
                return {"success": False, "error": "Usuario no permitido"}
    
            # If user is allowed, use DB data for registration
            db_id, db_nombre, db_apellido, db_email = matching_user
    
            # Register entry/exit
            now = datetime.now()
            fecha = now.strftime("%Y-%m-%d")
            hora = now.strftime("%H:%M:%S")
            dia = now.strftime("%A")
    
            cursor.execute('''
                INSERT INTO registros (fecha, hora, dia, nombre, apellido, email)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (fecha, hora, dia, db_nombre, db_apellido, db_email))
    
            conn.commit()
            registro_id = cursor.lastrowid
            conn.close()
    
            return {
                "success": True,
                "message": f"Registro exitoso: {db_nombre} {db_apellido}",
                "id": registro_id,
                "fecha": fecha,
                "hora": hora
            }
    
        except Exception as e:
            print(f"Database error: {str(e)}")
            return {"success": False, "error": f"Error en base de datos: {str(e)}"}
    
    def mostrar_resultado(self, success, title, message):
        # Crear una vista modal para mostrar el resultado
        modal = ModalView(size_hint=(0.8, 0.4))
        content = BoxLayout(orientation='vertical', padding=20, spacing=10)
        
        # Título
        title_label = Label(
            text=title,
            font_size='22sp',
            color=get_color_from_hex('#FFFFFF'),
            size_hint=(1, 0.3)
        )
        
        # Mensaje
        msg_label = Label(
            text=message,
            font_size='18sp',
            color=get_color_from_hex('#CCCCCC'),
            size_hint=(1, 0.5)
        )
        
        # Botón de cerrar
        close_button = Button(
            text="Cerrar",
            background_color=get_color_from_hex('#5D9CEC') if success else get_color_from_hex('#ED5565'),
            size_hint=(1, 0.2)
        )
        close_button.bind(on_release=modal.dismiss)
        
        # Añadir widgets al layout
        content.add_widget(title_label)
        content.add_widget(msg_label)
        content.add_widget(close_button)
        
        # Configurar color de fondo según resultado
        if success:
            color = get_color_from_hex('#4CAF50')
            modal.background_color = [color[0], color[1], color[2], 0.9]
        else:
            color = get_color_from_hex('#F44336')
            modal.background_color = [color[0], color[1], color[2], 0.9]
        
        # Mostrar el modal
        modal.add_widget(content)
        modal.open()
        
        # Cambiar el texto del status
        if success:
            self.status_label.text = "¡Registro exitoso!"
            self.status_label.color = get_color_from_hex('#4CAF50')
        else:
            self.status_label.text = "Error en el registro"
            self.status_label.color = get_color_from_hex('#F44336')
        
        # Restaurar color después de un tiempo
        Clock.schedule_once(self.reset_status_color, 3)
    
    def reset_status_color(self, dt):
        self.status_label.text = "Escanea un código QR"
        self.status_label.color = get_color_from_hex('#CCCCCC')
    
    def toggle_scanning(self, instance):
        self.is_scanning = not self.is_scanning
        if self.is_scanning:
            self.toggle_button.text = "Pausar"
            self.status_label.text = "Escanea un código QR"
        else:
            self.toggle_button.text = "Reanudar"
            self.status_label.text = "Escáner en pausa"
    
    def quit_app(self, instance):
        # Liberar la cámara
        self.capture.release()
        # Salir de la aplicación
        App.get_running_app().stop()

def verificar_horario(self, email, dia_semana, hora_actual):
    conn = sqlite3.connect(self.db_path)
    cursor = conn.cursor()
    
    # Buscar los bloques de horario para este usuario en este día
    cursor.execute("""
        SELECT h.hora_entrada, h.hora_salida 
        FROM horarios_asignados h
        JOIN usuarios_permitidos u ON h.usuario_id = u.id
        WHERE u.email = ? AND h.dia = ?
        ORDER BY h.hora_entrada
    """, (email, dia_semana))
    
    bloques = cursor.fetchall()
    conn.close()
    
    if not bloques:
        return False, "No tiene horario asignado para hoy"
    
    # Convertir hora actual a objeto datetime para comparar
    hora_dt = datetime.strptime(hora_actual, "%H:%M:%S").time()
    
    # Verificar si la hora actual está dentro de algún bloque
    for entrada, salida in bloques:
        hora_entrada = datetime.strptime(entrada, "%H:%M:%S").time()
        hora_salida = datetime.strptime(salida, "%H:%M:%S").time()
        
        if hora_entrada <= hora_dt <= hora_salida:
            return True, f"Dentro del horario ({entrada} - {salida})"
    
    # Si llegamos aquí, no está en ningún bloque
    # Encontrar el bloque más cercano
    bloques_dt = [(datetime.strptime(e, "%H:%M:%S").time(), 
                  datetime.strptime(s, "%H:%M:%S").time()) for e, s in bloques]
    
    # Ordenar por proximidad
    bloques_dt.sort(key=lambda b: 
        abs((datetime.combine(datetime.today(), hora_dt) - 
             datetime.combine(datetime.today(), b[0])).total_seconds()))
    
    proximo = bloques_dt[0]
    return False, f"Fuera de horario. Bloque más cercano: {proximo[0].strftime('%H:%M:%S')} - {proximo[1].strftime('%H:%M:%S')}"

class LectorQRApp(App):
    def build(self):
        # Configurar los colores de la ventana
        Window.clearcolor = get_color_from_hex('#303030')
        return LectorQR()

if __name__ == '__main__':
    # Necesitamos importar numpy para el polígono
    import numpy as np
    LectorQRApp().run()