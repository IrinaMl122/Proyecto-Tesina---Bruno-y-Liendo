from flask import Flask, render_template, render_template_string, request, redirect, url_for, session, flash, send_from_directory
from flask_mysqldb import MySQL
from flask_bcrypt import Bcrypt
import MySQLdb.cursors
import os
import secrets

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

# Configuración MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'admin123'  
app.config['MYSQL_DB'] = 'gestor_tareas'

mysql = MySQL(app)
bcrypt = Bcrypt(app)

@app.route('/')
def index():
    # Si el usuario está logueado, redirigir al dashboard
    if 'loggedin' in session:
        return redirect(url_for('dashboard'))
    
    return render_template('index.html')

@app.route('/home')
def home():
    return render_template('home.html')

# Compatibilidad con rutas antiguas mal referenciadas
@app.route('/style.css')
def legacy_style():
    return send_from_directory('static', 'styles.css')

@app.route('/mudkip.png')
def legacy_mudkip():
    return send_from_directory('static/img', 'mudkip.png')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password_candidate = request.form.get('password')

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM usuarios WHERE email = %s', (email,))
        account = cursor.fetchone()

        if account and bcrypt.check_password_hash(account['password'], password_candidate):
            session['loggedin'] = True
            session['id'] = account['id']
            session['nombre'] = account['nombre']
            flash('Has iniciado sesión correctamente.', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Usuario o contraseña incorrectos', 'danger')

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
        
        # Obtener proyectos recientes
        cursor.execute('SELECT titulo, estado, fecha_creacion FROM proyectos WHERE usuario_id = %s ORDER BY fecha_creacion DESC LIMIT 5', (user_id,))
        proyectos_recientes = cursor.fetchall()
        
        return render_template('dashboard.html', 
                             nombre=session.get('nombre'),
                             proyectos_activos=proyectos_activos,
                             proyectos_completados=proyectos_completados,
                             proyectos_cancelados=proyectos_cancelados,
                             total_proyectos=total_proyectos,
                             proyectos_recientes=proyectos_recientes)
    return redirect(url_for('login'))

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

@app.route('/logout')
def logout():
    session.clear()
    flash('Sesión cerrada', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)