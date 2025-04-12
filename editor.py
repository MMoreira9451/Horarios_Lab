import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import unicodedata

DB_PATH = "registro_qr.db"

def normalize_text(text):
    """Normaliza el texto: convierte a minúsculas y elimina acentos y ñ"""
    if text is None:
        return ""
    # Convertir a minúsculas
    text = text.lower()
    # Eliminar acentos
    text = ''.join(c for c in unicodedata.normalize('NFD', text)
                  if unicodedata.category(c) != 'Mn')
    # Reemplazar ñ por n
    text = text.replace('ñ', 'n')
    return text

# Function to fetch records of entries and exits
def fetch_users():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, fecha, hora, dia, nombre, apellido, email FROM registros")
    users = cursor.fetchall()
    conn.close()
    return users

# Cargar horarios asignados
def fetch_schedules():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Unir con la tabla de usuarios para obtener los datos completos
    cursor.execute("""
        SELECT h.id, u.nombre, u.apellido, u.email, h.dia, h.hora_entrada, h.hora_salida 
        FROM horarios_asignados h
        JOIN usuarios_permitidos u ON h.usuario_id = u.id
        ORDER BY u.nombre, u.apellido, h.dia, h.hora_entrada
    """)
    
    data = cursor.fetchall()
    conn.close()
    return data

# Eliminar horario
def delete_selected_schedule():
    selected_item = horarios_tree.selection()
    if not selected_item:
        messagebox.showwarning("Selección requerida", "Selecciona un horario para eliminar")
        return
    item = horarios_tree.item(selected_item)
    schedule_id = item['values'][0]
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM horarios_asignados WHERE id=?", (schedule_id,))
    conn.commit()
    conn.close()
    refresh_schedules()

# Refrescar tabla
def refresh_schedules():
    for row in horarios_tree.get_children():
        horarios_tree.delete(row)
    for row in fetch_schedules():
        horarios_tree.insert("", "end", values=row)

# MODIFICADO: Agregar nuevo horario
def add_schedule():
    # Obtener lista de usuarios permitidos
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre, apellido, email FROM usuarios_permitidos ORDER BY nombre, apellido")
    usuarios = cursor.fetchall()
    conn.close()
    
    if not usuarios:
        messagebox.showwarning("Sin usuarios", "No hay usuarios permitidos registrados")
        return
    
    window = tk.Toplevel(root)
    window.title("Agregar Horario")
    window.geometry("720x600")
    
    # Frame para seleccionar usuario
    user_frame = tk.LabelFrame(window, text="Seleccionar Usuario")
    user_frame.pack(fill="both", expand=True, padx=10, pady=5)
    
    # Lista de usuarios
    users_listbox = tk.Listbox(user_frame, width=50, height=8)
    users_listbox.pack(side=tk.LEFT, fill="both", expand=True, padx=5, pady=5)
    
    # Scrollbar para la lista
    scrollbar = tk.Scrollbar(user_frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    # Configurar scrollbar con listbox
    users_listbox.config(yscrollcommand=scrollbar.set)
    scrollbar.config(command=users_listbox.yview)
    
    # Llenar la lista con usuarios
    user_mapping = {}  # Para mapear índices a IDs de usuarios
    for i, (uid, nombre, apellido, email) in enumerate(usuarios):
        display_text = f"{nombre} {apellido} ({email})"
        users_listbox.insert(tk.END, display_text)
        user_mapping[i] = uid
    
    # Frame para los bloques de horario
    bloques_frame = tk.LabelFrame(window, text="Bloques de Horario")
    bloques_frame.pack(fill="both", expand=True, padx=10, pady=5)
    
    # Lista para almacenar los bloques
    bloques = []
    bloques_listbox = tk.Listbox(bloques_frame, width=50, height=5)
    bloques_listbox.pack(side=tk.LEFT, fill="both", expand=True, padx=5, pady=5)
    
    # Scrollbar para los bloques
    bloques_scrollbar = tk.Scrollbar(bloques_frame)
    bloques_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    bloques_listbox.config(yscrollcommand=bloques_scrollbar.set)
    bloques_scrollbar.config(command=bloques_listbox.yview)
    
    # Frame para detalles del bloque
    bloque_frame = tk.LabelFrame(window, text="Configurar Bloque")
    bloque_frame.pack(fill="both", expand=True, padx=10, pady=5)
    
    tk.Label(bloque_frame, text="Día:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
    dia_combo = ttk.Combobox(bloque_frame, values=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"])
    dia_combo.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
    
    tk.Label(bloque_frame, text="Hora Entrada:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
    hora_entrada = tk.Entry(bloque_frame)
    hora_entrada.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
    hora_entrada.insert(0, "08:00:00")
    
    tk.Label(bloque_frame, text="Hora Salida:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
    hora_salida = tk.Entry(bloque_frame)
    hora_salida.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
    hora_salida.insert(0, "12:00:00")
    
    # Botón para agregar bloque
    agregar_bloque_btn = tk.Button(bloque_frame, text="AGREGAR BLOQUE", bg="#2196F3", fg="white", 
                                  font=("Arial", 10, "bold"), height=2)
    agregar_bloque_btn.grid(row=3, column=0, columnspan=2, sticky="ew", padx=5, pady=10)
    
    def agregar_bloque():
        dia = dia_combo.get()
        h_entrada = hora_entrada.get()
        h_salida = hora_salida.get()
        
        if not dia or not h_entrada or not h_salida:
            messagebox.showwarning("Datos incompletos", "Complete todos los campos del bloque")
            return
        
        bloque = {
            "dia": dia,
            "hora_entrada": h_entrada,
            "hora_salida": h_salida
        }
        
        bloques.append(bloque)
        bloques_listbox.insert(tk.END, f"{dia}: {h_entrada} - {h_salida}")
        
        # Limpiar campos para el siguiente bloque
        hora_entrada.delete(0, tk.END)
        hora_entrada.insert(0, h_salida)
        hora_salida.delete(0, tk.END)
        hora_salida.insert(0, "17:00:00")
    
    agregar_bloque_btn.config(command=agregar_bloque)
    
    # Botones para gestionar bloques
    bloques_btn_frame = tk.Frame(window)
    bloques_btn_frame.pack(fill="x", padx=10, pady=5)
    
    def quitar_bloque():
        selected = bloques_listbox.curselection()
        if not selected:
            messagebox.showwarning("Selección requerida", "Selecciona un bloque para eliminar")
            return
        
        idx = selected[0]
        bloques.pop(idx)
        bloques_listbox.delete(idx)
    
    tk.Button(bloques_btn_frame, text="Quitar Bloque", command=quitar_bloque).pack(side=tk.LEFT, padx=5)
    
    # Botones de acción
    button_frame = tk.Frame(window)
    button_frame.pack(fill="x", padx=10, pady=10)
    
    # Traducir días de español a inglés
    dia_mapping = {
        "Lunes": "Monday",
        "Martes": "Tuesday",
        "Miércoles": "Wednesday",
        "Jueves": "Thursday",
        "Viernes": "Friday",
        "Sábado": "Saturday",
        "Domingo": "Sunday"
    }
    
    def save():
        # Validar selección de usuario
        selected_indices = users_listbox.curselection()
        
        if not selected_indices:
            messagebox.showwarning("Selección requerida", "Por favor selecciona un usuario")
            return
        
        if not bloques:
            messagebox.showwarning("Bloques requeridos", "Agrega al menos un bloque de horario")
            return
        
        selected_index = selected_indices[0]
        usuario_id = user_mapping[selected_index]
        
        # Guardar cada bloque de horario
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        success = False
        
        try:
            for bloque in bloques:
                # Traducir el día de español a inglés
                dia_en = dia_mapping.get(bloque["dia"], bloque["dia"])
                
                cursor.execute('''
                    INSERT INTO horarios_asignados (usuario_id, dia, hora_entrada, hora_salida)
                    VALUES (?, ?, ?, ?)
                    ''', (usuario_id, dia_en, bloque["hora_entrada"], bloque["hora_salida"]))
                conn.commit()
            success = True
            messagebox.showinfo("Éxito", f"Se agregaron {len(bloques)} bloques de horario")
        except Exception as e:
            messagebox.showerror("Error", f"Error al guardar: {str(e)}")
        finally:
            conn.close()
        
        if success:
            window.destroy()
            refresh_schedules()
    
    tk.Button(button_frame, text="Guardar", command=save, width=10).pack(side=tk.LEFT, padx=5)
    tk.Button(button_frame, text="Cancelar", command=window.destroy, width=10).pack(side=tk.RIGHT, padx=5)

# Function to fetch permitted users
def fetch_permitted_users():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre, apellido, email FROM usuarios_permitidos")
    users = cursor.fetchall()
    conn.close()
    return users

# Function to update entries/exits
def update_user(user_id, nombre, apellido, email):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE registros SET nombre=?, apellido=?, email=? WHERE id=?", (nombre, apellido, email, user_id))
    conn.commit()
    conn.close()

# Function to update permitted users
def update_permitted_user(user_id, nombre, apellido, email):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE usuarios_permitidos SET nombre=?, apellido=?, email=? WHERE id=?", (nombre, apellido, email, user_id))
    conn.commit()
    conn.close()

# Function to delete entries/exits
def delete_selected_user():
    selected_item = registros_tree.selection()
    if not selected_item:
        messagebox.showwarning("Selección requerida", "Por favor selecciona un registro para eliminar")
        return
    
    item = registros_tree.item(selected_item)
    user_id = item['values'][0]
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM registros WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    refresh_users()

# Function to delete permitted users
def delete_selected_user_permitted():
    selected_item = permitidos_tree.selection()
    if not selected_item:
        messagebox.showwarning("Selección requerida", "Por favor selecciona un usuario para eliminar")
        return
    
    item = permitidos_tree.item(selected_item)
    user_id = item['values'][0]
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM usuarios_permitidos WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    refresh_permitted_users()

# Function to add a new entry/exit
def add_user(nombre, apellido, email):
    from datetime import datetime
    now = datetime.now()
    fecha = now.strftime("%Y-%m-%d")
    hora = now.strftime("%H:%M:%S")
    dia = now.strftime("%A")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO registros (fecha, hora, dia, nombre, apellido, email) VALUES (?, ?, ?, ?, ?, ?)", (fecha, hora, dia, nombre, apellido, email))
    conn.commit()
    conn.close()

# Function to add permitted users
def add_permitted_user(nombre, apellido, email):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Comprobar si ya existe un usuario similar
    norm_nombre = normalize_text(nombre)
    norm_apellido = normalize_text(apellido)
    norm_email = normalize_text(email)
    
    cursor.execute("SELECT id, nombre, apellido, email FROM usuarios_permitidos")
    all_users = cursor.fetchall()
    
    for user in all_users:
        user_id, db_nombre, db_apellido, db_email = user
        if (normalize_text(db_nombre) == norm_nombre and 
            normalize_text(db_apellido) == norm_apellido and 
            normalize_text(db_email) == norm_email):
            messagebox.showinfo("Usuario Existente", 
                               f"Ya existe un usuario similar: {db_nombre} {db_apellido} ({db_email})")
            conn.close()
            return
    
    # Añadir nuevo usuario si no existe uno similar
    cursor.execute("INSERT INTO usuarios_permitidos (nombre, apellido, email) VALUES (?, ?, ?)", (nombre, apellido, email))
    conn.commit()
    conn.close()

# Function to edit a selected entry/exit
def edit_user():
    selected_item = registros_tree.selection()
    if not selected_item:
        messagebox.showwarning("Selección requerida", "Por favor selecciona un registro para editar")
        return
    
    item = registros_tree.item(selected_item)
    user_id, fecha, hora, dia, nombre, apellido, email = item['values']
    
    edit_window = tk.Toplevel(root)
    edit_window.title("Editar Registro")
    
    tk.Label(edit_window, text="Fecha:").grid(row=0, column=0)
    tk.Label(edit_window, text=fecha).grid(row=0, column=1)
    
    tk.Label(edit_window, text="Hora:").grid(row=1, column=0)
    tk.Label(edit_window, text=hora).grid(row=1, column=1)
    
    tk.Label(edit_window, text="Día:").grid(row=2, column=0)
    tk.Label(edit_window, text=dia).grid(row=2, column=1)
    
    tk.Label(edit_window, text="Nombre:").grid(row=3, column=0)
    nombre_entry = tk.Entry(edit_window)
    nombre_entry.insert(0, nombre)
    nombre_entry.grid(row=3, column=1)
    
    tk.Label(edit_window, text="Apellido:").grid(row=4, column=0)
    apellido_entry = tk.Entry(edit_window)
    apellido_entry.insert(0, apellido)
    apellido_entry.grid(row=4, column=1)
    
    tk.Label(edit_window, text="Email:").grid(row=5, column=0)
    email_entry = tk.Entry(edit_window)
    email_entry.insert(0, email)
    email_entry.grid(row=5, column=1)
    
    def save_changes():
        update_user(user_id, nombre_entry.get(), apellido_entry.get(), email_entry.get())
        edit_window.destroy()
        refresh_users()
    
    tk.Button(edit_window, text="Guardar", command=save_changes).grid(row=6, columnspan=2)

# Function to edit permitted users
def edit_permitted_user():
    selected_item = permitidos_tree.selection()
    if not selected_item:
        messagebox.showwarning("Selección requerida", "Por favor selecciona un usuario para editar")
        return
    
    item = permitidos_tree.item(selected_item)
    user_id, nombre, apellido, email = item['values']
    
    edit_window = tk.Toplevel(root)
    edit_window.title("Editar Usuario Permitido")
    
    tk.Label(edit_window, text="Nombre:").grid(row=0, column=0)
    nombre_entry = tk.Entry(edit_window)
    nombre_entry.insert(0, nombre)
    nombre_entry.grid(row=0, column=1)
    
    tk.Label(edit_window, text="Apellido:").grid(row=1, column=0)
    apellido_entry = tk.Entry(edit_window)
    apellido_entry.insert(0, apellido)
    apellido_entry.grid(row=1, column=1)
    
    tk.Label(edit_window, text="Email:").grid(row=2, column=0)
    email_entry = tk.Entry(edit_window)
    email_entry.insert(0, email)
    email_entry.grid(row=2, column=1)
    
    def save_changes():
        update_permitted_user(user_id, nombre_entry.get(), apellido_entry.get(), email_entry.get())
        edit_window.destroy()
        refresh_permitted_users()
    
    tk.Button(edit_window, text="Guardar", command=save_changes).grid(row=3, columnspan=2)

# Function to refresh entry/exit records
def refresh_users():
    for row in registros_tree.get_children():
        registros_tree.delete(row)
    for user in fetch_users():
        registros_tree.insert("", "end", values=user)

# Function to refresh permitted users
def refresh_permitted_users():
    for row in permitidos_tree.get_children():
        permitidos_tree.delete(row)
    for user in fetch_permitted_users():
        permitidos_tree.insert("", "end", values=user)

# Function to add a new permitted user
def add_new_user_permitted():
    add_window = tk.Toplevel(root)
    add_window.title("Agregar Usuario Permitido")
    
    tk.Label(add_window, text="Nombre:").grid(row=0, column=0)
    nombre_entry = tk.Entry(add_window)
    nombre_entry.grid(row=0, column=1)
    
    tk.Label(add_window, text="Apellido:").grid(row=1, column=0)
    apellido_entry = tk.Entry(add_window)
    apellido_entry.grid(row=1, column=1)
    
    tk.Label(add_window, text="Email:").grid(row=2, column=0)
    email_entry = tk.Entry(add_window)
    email_entry.grid(row=2, column=1)
    
    def save_new_user():
        add_permitted_user(nombre_entry.get(), apellido_entry.get(), email_entry.get())
        add_window.destroy()
        refresh_permitted_users()
    
    tk.Button(add_window, text="Agregar", command=save_new_user).grid(row=3, columnspan=2)

# Main window
root = tk.Tk()
root.title("Control de Horarios y Usuarios Permitidos")

# Tabs
notebook = ttk.Notebook(root)
notebook.pack(expand=True, fill="both")

# Tab for entries/exits
registros_frame = tk.Frame(notebook)
notebook.add(registros_frame, text="Registros")

# Tab de horarios
horarios_frame = tk.Frame(notebook)
notebook.add(horarios_frame, text="Horarios Asignados")

horarios_tree = ttk.Treeview(horarios_frame, columns=("ID", "Nombre", "Apellido", "Email", "Día", "Hora Inicio", "Hora Fin"), show="headings")
for col in ("ID", "Nombre", "Apellido", "Email", "Día", "Hora Inicio", "Hora Fin"):
    horarios_tree.heading(col, text=col)
    horarios_tree.column(col, width=100)

horarios_tree.pack(fill="both", expand=True)

btn_frame = tk.Frame(horarios_frame)
btn_frame.pack()

tk.Button(btn_frame, text="Agregar", command=add_schedule).pack(side=tk.LEFT)
tk.Button(btn_frame, text="Eliminar", command=delete_selected_schedule).pack(side=tk.LEFT)
# Añadir botón de refrescar para permitir actualización manual
tk.Button(btn_frame, text="Refrescar", command=refresh_schedules).pack(side=tk.LEFT)

refresh_schedules()

registros_tree = ttk.Treeview(registros_frame, columns=("ID", "Fecha", "Hora", "Día", "Nombre", "Apellido", "Email"), show="headings")
for col in ("ID", "Fecha", "Hora", "Día", "Nombre", "Apellido", "Email"):
    registros_tree.heading(col, text=col)
    registros_tree.column(col, width=120)

registros_tree.pack(fill="both", expand=True)

registros_btn_frame = tk.Frame(registros_frame)
registros_btn_frame.pack()

tk.Button(registros_btn_frame, text="Editar", command=edit_user).pack(side=tk.LEFT)
tk.Button(registros_btn_frame, text="Eliminar", command=delete_selected_user).pack(side=tk.LEFT)

# Tab for permitted users
permitidos_frame = tk.Frame(notebook)
notebook.add(permitidos_frame, text="Usuarios Permitidos")

permitidos_tree = ttk.Treeview(permitidos_frame, columns=("ID", "Nombre", "Apellido", "Email"), show="headings")
for col in ("ID", "Nombre", "Apellido", "Email"):
    permitidos_tree.heading(col, text=col)
    permitidos_tree.column(col, width=150)

permitidos_tree.pack(fill="both", expand=True)

permitidos_btn_frame = tk.Frame(permitidos_frame)
permitidos_btn_frame.pack()

tk.Button(permitidos_btn_frame, text="Agregar", command=add_new_user_permitted).pack(side=tk.LEFT)
tk.Button(permitidos_btn_frame, text="Editar", command=edit_permitted_user).pack(side=tk.LEFT)
tk.Button(permitidos_btn_frame, text="Eliminar", command=delete_selected_user_permitted).pack(side=tk.LEFT)

refresh_users()
refresh_permitted_users()

root.mainloop()