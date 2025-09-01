from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
from flask_bcrypt import Bcrypt
import MySQLdb.cursors

app = Flask(__name__)
app.secret_key = ''   

# Configuración MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'admin123'  
app.config['MYSQL_DB'] = 'gestor_tareas'

mysql = MySQL(app)
bcrypt = Bcrypt(app)

@app.route('/')
def index():
    return render_template('index.html')

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

        print(f"Datos recibidos: {nombre}, {email}, {password}, {confirm_password}")

        if not (nombre and email and password and confirm_password):
            flash('Completá todos los campos', 'warning')
            return redirect(url_for('register'))

        if password != confirm_password:
            flash('Las contraseñas no coinciden', 'warning')
            return redirect(url_for('register'))

        try:
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('SELECT * FROM usuarios WHERE email = %s', (email,))
            account = cursor.fetchone()
            if account:
                flash('El correo ya está registrado', 'danger')
                return redirect(url_for('register'))

            pw_hash = bcrypt.generate_password_hash(password).decode('utf-8')
            print(f"Hash generado: {pw_hash}")
            cursor.execute('INSERT INTO usuarios (nombre, email, password) VALUES (%s, %s, %s)', (nombre, email, pw_hash))
            mysql.connection.commit()
            flash('Registro exitoso. Ya podes iniciar sesión.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            print(f"Error en el registro: {e}")
            flash('Error interno al registrar usuario.', 'danger')
            return redirect(url_for('register'))

    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'loggedin' in session:
        # Aquí podés consultar proyectos/tareas después
        return render_template('dashboard.html', nombre=session.get('nombre'))
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.clear()
    flash('Sesión cerrada', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
