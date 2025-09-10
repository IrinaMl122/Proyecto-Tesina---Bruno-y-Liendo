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
    html = """
    <!DOCTYPE html>
    <html lang=\"es\">
    <head>
        <meta charset=\"UTF-8\">
        <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
        <title>ESCALOR - Inicio</title>
        <link rel=\"stylesheet\" href=\"{{ url_for('static', filename='style.css') }}?v=4\">
    </head>
    <body>
        <header class=\"site-header\">
            <div class=\"header-inner\"> 
                <img class=\"logo\" src=\"{{ url_for('static', filename='img/mudkip.png') }}\" alt=\"Logo\"> 
                <h1 class=\"titulo\">ESCALOR</h1>
                <nav>
                    <a href=\"{{ url_for('index') }}\">Inicio</a> |
                    {% if session.get('loggedin') %}
                        <a href=\"{{ url_for('logout') }}\">Salir</a>
                    {% else %}
                        <a href=\"{{ url_for('login') }}\">Inicio de sesión</a> |
                        <a href=\"{{ url_for('register') }}\">Registro</a>
                    {% endif %}
                </nav>
            </div>
        </header>

        <main class=\"container\">
            <section class=\"panel\">
                <div class=\"panel-inner\">
                    <h2 class=\"panel-title\" style=\"text-align:center;\">🔐 INICIO DE SESIÓN</h2>
                    <div class=\"form\" style=\"text-align:center;\">
                        <a href=\"{{ url_for('login') }}\"><button class=\"btn-primary\" type=\"button\">Iniciar sesión</button></a>
                    </div>
                </div>
            </section>

            <section class=\"panel\">
                <div class=\"panel-inner\">
                    <h2 class=\"panel-title\" style=\"text-align:center;\">🆕 REGISTRARSE</h2>
                    <div class=\"form\" style=\"text-align:center;\">
                        <a href=\"{{ url_for('register') }}\"><button class=\"btn-primary\" type=\"button\">Crear cuenta</button></a>
                    </div>
                </div>
            </section>
        </main>

        <footer class=\"site-footer\"><small>© 2025 ESCALOR</small></footer>
    </body>
    </html>
    """
    return render_template_string(html)

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
        return render_template('dashboard.html', nombre=session.get('nombre'))
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.clear()
    flash('Sesión cerrada', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)