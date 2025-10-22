from flask import Flask, render_template, render_template_string, request, redirect, url_for, session, flash, send_from_directory, send_file
from flask_mysqldb import MySQL
from flask_bcrypt import Bcrypt
import MySQLdb.cursors
import os
import secrets
from werkzeug.utils import secure_filename

app = Flask(__name__, static_folder='static', template_folder='templates', static_url_path='/static')
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # desactivar caché de estáticos
app.config['TEMPLATES_AUTO_RELOAD'] = True

@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response
# SECRET_KEY para sesiones y flashing
# Usa variable de entorno si está definida, de lo contrario genera una clave segura en runtime.
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY') or os.environ.get('SECRET_KEY') or secrets.token_hex(32)

# Configuración de sesiones
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hora
app.config['SESSION_COOKIE_SECURE'] = False  # Para desarrollo local
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Archivos adjuntos
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOADS_PATH = os.path.join(BASE_DIR, 'uploads')
os.makedirs(UPLOADS_PATH, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOADS_PATH
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB por archivo
ALLOWED_EXTENSIONS = set(['png','jpg','jpeg','gif','pdf','doc','docx','xls','xlsx','txt','csv','zip'])

def is_allowed_file(filename: str):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Configuración MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'admin123'  
app.config['MYSQL_DB'] = 'gestor_tareas'

mysql = MySQL(app)
bcrypt = Bcrypt(app)

@app.route('/')
def index():
    # Siempre mostrar la página de inicio, sin redirigir automáticamente
    return render_template('index.html')

@app.route('/home')
def home():
    return render_template('home.html')

# Compatibilidad con rutas antiguas mal referenciadas
@app.route('/style.css')
def legacy_style():
    return send_from_directory('static', 'styles.css')

@app.route('/image.png')
def legacy_logo():
    return send_from_directory('static/img', 'image.png')

# Easter egg: página con trono y mudkip
@app.route('/easter-egg')
def easter_egg():
    return render_template('easter_egg.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identificador = request.form.get('identificador')
        password_candidate = request.form.get('password')

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        # Permitir login por email o por nombre de usuario
        cursor.execute('SELECT * FROM usuarios WHERE email = %s OR nombre = %s', (identificador, identificador))
        account = cursor.fetchone()

        if account and bcrypt.check_password_hash(account['password'], password_candidate):
            session['loggedin'] = True
            session['id'] = account['id']
            session['nombre'] = account['nombre']
            flash('Has iniciado sesión correctamente.', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Usuario/email o contraseña incorrectos', 'danger')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if not (nombre and email and password and confirm_password):
            flash('Completá todos los campos', 'warning')
            return redirect(url_for('register'))

        if password != confirm_password:
            flash('Las contraseñas no coinciden', 'warning')
            return redirect(url_for('register'))

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM usuarios WHERE email = %s', (email,))
        account = cursor.fetchone()
        if account:
            flash('El correo ya está registrado', 'danger')
            return redirect(url_for('register'))

        pw_hash = bcrypt.generate_password_hash(password).decode('utf-8')
        cursor.execute('INSERT INTO usuarios (nombre, email, password) VALUES (%s, %s, %s)', (nombre, email, pw_hash))
        mysql.connection.commit()
        flash('Registro exitoso. Ya podes iniciar sesión.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'loggedin' in session:
        user_id = session.get('id')
        
        # Obtener estadísticas de proyectos
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        # Contar proyectos en proceso
        cursor.execute('SELECT COUNT(*) as count FROM proyectos WHERE usuario_id = %s AND estado = "en proceso"', (user_id,))
        proyectos_activos = cursor.fetchone()['count']
        
        # Contar proyectos realizados
        cursor.execute('SELECT COUNT(*) as count FROM proyectos WHERE usuario_id = %s AND estado = "realizado"', (user_id,))
        proyectos_completados = cursor.fetchone()['count']
        
        # Contar proyectos cancelados
        cursor.execute('SELECT COUNT(*) as count FROM proyectos WHERE usuario_id = %s AND estado = "cancelado"', (user_id,))
        proyectos_cancelados = cursor.fetchone()['count']
        
        # Total de proyectos
        cursor.execute('SELECT COUNT(*) as count FROM proyectos WHERE usuario_id = %s', (user_id,))
        total_proyectos = cursor.fetchone()['count']
        
        # Obtener proyectos pendientes/en proceso únicamente (excluir realizados y cancelados)
        cursor.execute('''
            SELECT id, titulo, estado, fecha_creacion
            FROM proyectos
            WHERE usuario_id = %s AND (estado = "en proceso" OR estado = "pendiente" OR estado IS NULL)
            ORDER BY fecha_creacion DESC LIMIT 5
        ''', (user_id,))
        proyectos_recientes = cursor.fetchall()
        
        return render_template('dashboard.html', 
                             nombre=session.get('nombre'),
                             proyectos_activos=proyectos_activos,
                             proyectos_completados=proyectos_completados,
                             proyectos_cancelados=proyectos_cancelados,
                             total_proyectos=total_proyectos,
                             proyectos_recientes=proyectos_recientes)
    return redirect(url_for('index'))

# Configuración de cuenta
@app.route('/configuracion', methods=['GET'])
def configuracion():
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT id, nombre, email FROM usuarios WHERE id = %s', (session.get('id'),))
    usuario = cursor.fetchone()
    return render_template('configuracion.html', usuario=usuario)

@app.route('/configuracion/actualizar_perfil', methods=['POST'])
def actualizar_perfil():
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    nombre = request.form.get('nombre')
    email = request.form.get('email')
    if not nombre or not email:
        flash('Nombre y email son obligatorios', 'warning')
        return redirect(url_for('configuracion'))
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    # Verificar email duplicado en otro usuario
    cursor.execute('SELECT id FROM usuarios WHERE email = %s AND id <> %s', (email, session.get('id')))
    existe = cursor.fetchone()
    if existe:
        flash('El email ya está en uso por otro usuario', 'danger')
        return redirect(url_for('configuracion'))
    cursor.execute('UPDATE usuarios SET nombre = %s, email = %s WHERE id = %s', (nombre, email, session.get('id')))
    mysql.connection.commit()
    session['nombre'] = nombre
    flash('Perfil actualizado', 'success')
    return redirect(url_for('configuracion'))

@app.route('/configuracion/cambiar_contrasena', methods=['POST'])
def cambiar_contrasena():
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    actual = request.form.get('password_actual')
    nueva = request.form.get('password_nueva')
    confirm = request.form.get('password_confirm')
    if not (actual and nueva and confirm):
        flash('Completá todos los campos', 'warning')
        return redirect(url_for('configuracion'))
    if nueva != confirm:
        flash('La confirmación no coincide', 'danger')
        return redirect(url_for('configuracion'))
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT password FROM usuarios WHERE id = %s', (session.get('id'),))
    row = cursor.fetchone()
    if not row or not bcrypt.check_password_hash(row['password'], actual):
        flash('La contraseña actual es incorrecta', 'danger')
        return redirect(url_for('configuracion'))
    pw_hash = bcrypt.generate_password_hash(nueva).decode('utf-8')
    cursor.execute('UPDATE usuarios SET password = %s WHERE id = %s', (pw_hash, session.get('id')))
    mysql.connection.commit()
    flash('Contraseña actualizada', 'success')
    return redirect(url_for('configuracion'))

@app.route('/configuracion/borrar_cuenta', methods=['POST'])
def borrar_cuenta():
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    user_id = session.get('id')
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    # Eliminar datos asociados (tareas de los proyectos del usuario) antes de borrar proyectos
    cursor.execute('DELETE t FROM tareas t JOIN proyectos p ON p.id = t.proyecto_id WHERE p.usuario_id = %s', (user_id,))
    # Luego eliminar proyectos del usuario y finalmente el usuario
    cursor.execute('DELETE FROM proyectos WHERE usuario_id = %s', (user_id,))
    cursor.execute('DELETE FROM usuarios WHERE id = %s', (user_id,))
    mysql.connection.commit()
    session.clear()
    flash('Cuenta eliminada correctamente', 'info')
    return redirect(url_for('index'))

@app.route('/crear_proyecto', methods=['GET', 'POST'])
def crear_proyecto():
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        titulo = request.form.get('titulo')
        descripcion = request.form.get('descripcion')
        
        if not titulo:
            flash('El título es obligatorio', 'warning')
            return redirect(url_for('crear_proyecto'))
        
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('''INSERT INTO proyectos (usuario_id, titulo, descripcion, estado, fecha_creacion) 
                         VALUES (%s, %s, %s, 'en proceso', NOW())''', 
                      (session.get('id'), titulo, descripcion or None))
        mysql.connection.commit()
        
        flash('Proyecto creado exitosamente', 'success')
        return redirect(url_for('ver_proyectos'))
    
    return render_template('crear_proyecto.html')

@app.route('/ver_proyectos')
def ver_proyectos():
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('''SELECT * FROM proyectos WHERE usuario_id = %s 
                     ORDER BY fecha_creacion DESC''', (session.get('id'),))
    proyectos = cursor.fetchall()
    
    return render_template('ver_proyectos.html', proyectos=proyectos)

@app.route('/cambiar_estado/<int:proyecto_id>', methods=['POST'])
def cambiar_estado(proyecto_id):
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    
    nuevo_estado = request.form.get('estado')
    
    if not nuevo_estado or nuevo_estado not in ['en proceso', 'realizado', 'cancelado']:
        flash('Estado inválido', 'danger')
        return redirect(url_for('ver_proyectos'))
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    # Verificar que el proyecto pertenece al usuario
    cursor.execute('SELECT id FROM proyectos WHERE id = %s AND usuario_id = %s', (proyecto_id, session.get('id')))
    proyecto = cursor.fetchone()
    
    if not proyecto:
        flash('Proyecto no encontrado', 'danger')
        return redirect(url_for('ver_proyectos'))
    
    # Actualizar el estado
    cursor.execute('UPDATE proyectos SET estado = %s WHERE id = %s AND usuario_id = %s', 
                  (nuevo_estado, proyecto_id, session.get('id')))
    mysql.connection.commit()
    
    flash(f'Estado cambiado a: {nuevo_estado.title()}', 'success')
    return redirect(url_for('ver_proyectos'))

@app.route('/eliminar_proyecto/<int:proyecto_id>', methods=['POST'])
def eliminar_proyecto(proyecto_id):
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    # Verificar pertenencia
    cursor.execute('SELECT id FROM proyectos WHERE id = %s AND usuario_id = %s', (proyecto_id, session.get('id')))
    proyecto = cursor.fetchone()
    if not proyecto:
        flash('Proyecto no encontrado', 'danger')
        return redirect(url_for('ver_proyectos'))
    # Eliminar tareas asociadas y luego el proyecto
    cursor.execute('DELETE FROM tareas WHERE proyecto_id = %s', (proyecto_id,))
    cursor.execute('DELETE FROM proyectos WHERE id = %s', (proyecto_id,))
    mysql.connection.commit()
    flash('Proyecto eliminado', 'info')
    return redirect(url_for('ver_proyectos'))

# ------------------ TAREAS POR PROYECTO ------------------
@app.route('/proyectos/<int:proyecto_id>/tareas')
def tareas_por_proyecto(proyecto_id):
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    # validar pertenencia
    cursor.execute('SELECT id, titulo FROM proyectos WHERE id = %s AND usuario_id = %s', (proyecto_id, session.get('id')))
    proyecto = cursor.fetchone()
    if not proyecto:
        flash('Proyecto no encontrado', 'danger')
        return redirect(url_for('ver_proyectos'))
    cursor.execute('SELECT id, titulo, descripcion, fecha_limite, estado FROM tareas WHERE proyecto_id = %s ORDER BY id DESC', (proyecto_id,))
    tareas = cursor.fetchall()
    return render_template('tareas.html', proyecto=proyecto, tareas=tareas)

@app.route('/proyectos/<int:proyecto_id>/tareas/crear', methods=['POST'])
def crear_tarea(proyecto_id):
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    titulo = request.form.get('titulo')
    descripcion = request.form.get('descripcion') or None
    fecha_limite = request.form.get('fecha_limite') or None
    if not titulo:
        flash('El título es obligatorio', 'warning')
        return redirect(url_for('tareas_por_proyecto', proyecto_id=proyecto_id))
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT id FROM proyectos WHERE id = %s AND usuario_id = %s', (proyecto_id, session.get('id')))
    if not cursor.fetchone():
        flash('Proyecto no encontrado', 'danger')
        return redirect(url_for('ver_proyectos'))
    cursor.execute('INSERT INTO tareas (proyecto_id, titulo, descripcion, fecha_limite, estado) VALUES (%s, %s, %s, %s, %s)', (proyecto_id, titulo, descripcion, fecha_limite, 'pendiente'))
    mysql.connection.commit()
    flash('Tarea creada', 'success')
    return redirect(url_for('tareas_por_proyecto', proyecto_id=proyecto_id))

@app.route('/tareas/<int:tarea_id>/editar', methods=['GET', 'POST'])
def editar_tarea(tarea_id):
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('''SELECT t.*, p.usuario_id FROM tareas t
                      JOIN proyectos p ON p.id = t.proyecto_id
                      WHERE t.id = %s''', (tarea_id,))
    tarea = cursor.fetchone()
    if not tarea or tarea['usuario_id'] != session.get('id'):
        flash('Tarea no encontrada', 'danger')
        return redirect(url_for('ver_proyectos'))
    if request.method == 'POST':
        titulo = request.form.get('titulo')
        descripcion = request.form.get('descripcion') or None
        fecha_limite = request.form.get('fecha_limite') or None
        estado = request.form.get('estado')
        if not titulo:
            flash('El título es obligatorio', 'warning')
            return redirect(url_for('editar_tarea', tarea_id=tarea_id))
        if estado not in ['pendiente', 'en proceso', 'realizado', 'cancelado']:
            flash('Estado inválido', 'danger')
            return redirect(url_for('editar_tarea', tarea_id=tarea_id))
        cursor.execute('UPDATE tareas SET titulo=%s, descripcion=%s, fecha_limite=%s, estado=%s WHERE id=%s', (titulo, descripcion, fecha_limite, estado, tarea_id))
        mysql.connection.commit()
        flash('Tarea actualizada', 'success')
        return redirect(url_for('tareas_por_proyecto', proyecto_id=tarea['proyecto_id']))
    # GET: cargar comentarios y adjuntos
    cursor.execute('SELECT c.id, c.contenido, c.fecha_creacion, u.nombre FROM comentarios c JOIN usuarios u ON u.id = c.usuario_id WHERE c.tarea_id = %s ORDER BY c.fecha_creacion DESC', (tarea_id,))
    comentarios = cursor.fetchall()
    cursor.execute('SELECT id, original_nombre, filename, mime, tamano, fecha_subida FROM adjuntos WHERE tarea_id = %s ORDER BY id DESC', (tarea_id,))
    adjuntos = cursor.fetchall()
    return render_template('editar_tarea.html', tarea=tarea, comentarios=comentarios, adjuntos=adjuntos)

@app.route('/tareas/<int:tarea_id>/eliminar', methods=['POST'])
def eliminar_tarea(tarea_id):
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('''SELECT t.id, t.proyecto_id, p.usuario_id FROM tareas t
                      JOIN proyectos p ON p.id = t.proyecto_id
                      WHERE t.id = %s''', (tarea_id,))
    row = cursor.fetchone()
    if not row or row['usuario_id'] != session.get('id'):
        flash('Tarea no encontrada', 'danger')
        return redirect(url_for('ver_proyectos'))
    # eliminar adjuntos de disco y bd
    cursor.execute('SELECT filename FROM adjuntos WHERE tarea_id = %s', (tarea_id,))
    files = cursor.fetchall()
    for f in files or []:
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], f['filename']))
        except Exception:
            pass
    cursor.execute('DELETE FROM adjuntos WHERE tarea_id = %s', (tarea_id,))
    cursor.execute('DELETE FROM comentarios WHERE tarea_id = %s', (tarea_id,))
    cursor.execute('DELETE FROM tareas WHERE id = %s', (tarea_id,))
    mysql.connection.commit()
    flash('Tarea eliminada', 'info')
    return redirect(url_for('tareas_por_proyecto', proyecto_id=row['proyecto_id']))

# -------- Comentarios de tareas --------
@app.route('/tareas/<int:tarea_id>/comentarios/crear', methods=['POST'])
def crear_comentario(tarea_id):
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    contenido = request.form.get('contenido')
    if not contenido:
        flash('El comentario no puede estar vacío', 'warning')
        return redirect(url_for('editar_tarea', tarea_id=tarea_id))
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('''INSERT INTO comentarios (tarea_id, usuario_id, contenido) VALUES (%s, %s, %s)''', (tarea_id, session.get('id'), contenido))
    mysql.connection.commit()
    flash('Comentario agregado', 'success')
    return redirect(url_for('editar_tarea', tarea_id=tarea_id))

# -------- Adjuntos de tareas --------
@app.route('/tareas/<int:tarea_id>/adjuntos/subir', methods=['POST'])
def subir_adjunto(tarea_id):
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    file = request.files.get('archivo')
    if not file or file.filename == '':
        flash('Seleccioná un archivo', 'warning')
        return redirect(url_for('editar_tarea', tarea_id=tarea_id))
    if not is_allowed_file(file.filename):
        flash('Tipo de archivo no permitido', 'danger')
        return redirect(url_for('editar_tarea', tarea_id=tarea_id))
    original = file.filename
    safe = secure_filename(original)
    unique_name = f"{tarea_id}_{secrets.token_hex(8)}_{safe}"
    dest_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
    file.save(dest_path)
    tamano = os.path.getsize(dest_path)
    mime = file.mimetype
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('INSERT INTO adjuntos (tarea_id, filename, original_nombre, mime, tamano) VALUES (%s,%s,%s,%s,%s)', (tarea_id, unique_name, original, mime, tamano))
    mysql.connection.commit()
    flash('Archivo subido', 'success')
    return redirect(url_for('editar_tarea', tarea_id=tarea_id))

@app.route('/adjuntos/<int:adjunto_id>/descargar')
def descargar_adjunto(adjunto_id):
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('''SELECT a.filename, a.original_nombre, p.usuario_id FROM adjuntos a
                      JOIN tareas t ON t.id = a.tarea_id
                      JOIN proyectos p ON p.id = t.proyecto_id
                      WHERE a.id = %s''', (adjunto_id,))
    row = cursor.fetchone()
    if not row or row['usuario_id'] != session.get('id'):
        flash('Archivo no encontrado', 'danger')
        return redirect(url_for('ver_proyectos'))
    path = os.path.join(app.config['UPLOAD_FOLDER'], row['filename'])
    return send_file(path, as_attachment=True, download_name=row['original_nombre'])

@app.route('/adjuntos/<int:adjunto_id>/eliminar', methods=['POST'])
def eliminar_adjunto(adjunto_id):
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('''SELECT a.id, a.filename, t.proyecto_id, p.usuario_id, t.id as tarea_id FROM adjuntos a
                      JOIN tareas t ON t.id = a.tarea_id
                      JOIN proyectos p ON p.id = t.proyecto_id
                      WHERE a.id = %s''', (adjunto_id,))
    row = cursor.fetchone()
    if not row or row['usuario_id'] != session.get('id'):
        flash('Archivo no encontrado', 'danger')
        return redirect(url_for('ver_proyectos'))
    try:
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], row['filename']))
    except Exception:
        pass
    cursor.execute('DELETE FROM adjuntos WHERE id = %s', (adjunto_id,))
    mysql.connection.commit()
    flash('Archivo eliminado', 'info')
    return redirect(url_for('editar_tarea', tarea_id=row['tarea_id']))

@app.route('/logout')
def logout():
    # Limpiar completamente la sesión
    session.clear()
    # Eliminar todas las cookies de sesión
    session.permanent = False
    flash('Sesión cerrada correctamente', 'info')
    return redirect(url_for('index'))


# Función para limpiar sesión expirada
@app.before_request
def check_session():
    # Si hay una sesión pero no está válida, limpiarla
    if 'loggedin' in session:
        # Verificar que el usuario aún existe en la base de datos
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT id FROM usuarios WHERE id = %s', (session.get('id'),))
        if not cursor.fetchone():
            session.clear()
            session.permanent = False

if __name__ == '__main__':
    app.run(debug=True)