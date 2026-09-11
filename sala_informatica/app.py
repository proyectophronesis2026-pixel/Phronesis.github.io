"""
Sistema de Gestión de la Sala de Informática
---------------------------------------------
Proyecto de aprendizaje - Sistemas Teleinformáticos

Backend en Flask. Sirve las páginas HTML (con Jinja2) y expone
una pequeña API en /api/computadores y /api/usuarios que el
JavaScript del frontend consume con fetch().

Hay tres roles de usuario:
  - 'admin'    puede añadir/eliminar cuentas y crear, editar o
               eliminar computadores.
  - 'editor'   puede editar la ficha (incluido el estado) de los
               computadores, pero NO puede eliminarlos ni entrar
               a la gestión de cuentas.
  - 'consulta' solo puede iniciar sesión y ver los computadores.

No existe registro público: las cuentas las crea un administrador
desde /usuarios. Al arrancar por primera vez se crean 2 cuentas
admin de ejemplo (ver sembrar_administradores más abajo).

Recuperación de contraseña por correo:
  - /recuperar pide el usuario o correo, genera un código de 6
    dígitos, lo guarda (con vencimiento) en la fila del usuario y
    lo envía por Gmail (ver enviar_codigo_por_correo más abajo).
  - /recuperar/verificar pide ese código + la contraseña nueva.
  - El código nunca se muestra en pantalla ni se imprime en la
    terminal: solo llega al correo configurado en la cuenta.

Cómo se organiza este archivo:
  1) Conexión y utilidades de base de datos
  2) Envío de correo (recuperación de contraseña)
  3) Utilidad para registrar la actividad de los usuarios
  4) Rutas de páginas (login, dashboard, ficha, gestión de usuarios)
  5) Rutas de recuperación de contraseña
  6) API REST de computadores
  7) API REST de usuarios
"""

from functools import wraps
from datetime import datetime, timedelta
import os
import secrets
import smtplib
import sqlite3
from email.mime.text import MIMEText

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

# Carga las variables de entorno definidas en el archivo .env (mismo
# directorio que este archivo). Así GMAIL_USUARIO y GMAIL_APP_PASSWORD
# no quedan escritas en el código: viven solo en .env, que está en
# .gitignore para que nunca se suba a un repositorio ni se comparta
# por accidente.
load_dotenv()

app = Flask(__name__)

# La secret_key es necesaria para que Flask pueda usar "session"
# (así sabe qué usuario tiene la sesión iniciada en el navegador).
# En un proyecto real esto NUNCA se deja escrito en el código.
app.secret_key = 'cambia-esta-clave-por-una-propia-antes-de-entregar'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, 'sala_informatica.db')

# Nombre y lema del proyecto: cambia estos dos valores y se actualizan
# automáticamente en TODAS las pantallas (no hace falta tocar cada HTML).
NOMBRE_PROYECTO = 'Phronesis'
LEMA_PROYECTO = 'Knowledge Systems · Sala de Informática'

# ------------------------------------------------------------------
# CONFIGURACIÓN DE CORREO (envío del código de recuperación por Gmail)
# ------------------------------------------------------------------
# Las credenciales NO están escritas aquí: se leen del archivo .env
# (en la misma carpeta que app.py) mediante load_dotenv(), así nunca
# quedan visibles dentro del código fuente.
#
#   GMAIL_USUARIO       -> el Gmail remitente, ej. prhonesis387@gmail.com
#   GMAIL_APP_PASSWORD  -> una "contraseña de aplicación" de 16 caracteres
#                          (NO la contraseña normal de la cuenta de Gmail)
#
# Este proyecto ya trae un archivo .env con esos dos valores. Si el
# envío falla, casi siempre es porque GMAIL_APP_PASSWORD no es una
# contraseña de aplicación real (ver instrucciones en el README para
# generarla desde https://myaccount.google.com/apppasswords).
#
# Mientras estas dos variables no estén definidas (o sean inválidas),
# /recuperar mostrará un aviso indicando que el envío de correo no
# está configurado — el código NUNCA se imprime en la terminal ni se
# muestra en pantalla.
GMAIL_USUARIO = os.environ.get('GMAIL_USUARIO')
GMAIL_APP_PASSWORD = os.environ.get('GMAIL_APP_PASSWORD')
CODIGO_VIGENCIA_MINUTOS = 15


def enviar_codigo_por_correo(destinatario, codigo):
    """Envía el código de verificación al Gmail del usuario.
    Lanza una excepción si el correo no está configurado o si Gmail
    rechaza el envío (credenciales inválidas, sin conexión, etc.)."""
    if not GMAIL_USUARIO or not GMAIL_APP_PASSWORD:
        raise RuntimeError(
            'El envío de correo no está configurado: definan las variables '
            'de entorno GMAIL_USUARIO y GMAIL_APP_PASSWORD.'
        )

    cuerpo = (
        f'Hola,\n\n'
        f'Recibimos una solicitud para restablecer la contraseña de tu cuenta '
        f'en {NOMBRE_PROYECTO}.\n\n'
        f'Tu código de verificación es:\n\n'
        f'    {codigo}\n\n'
        f'Este código vence en {CODIGO_VIGENCIA_MINUTOS} minutos y solo se '
        f'puede usar una vez.\n\n'
        f'Si tú no solicitaste este cambio, puedes ignorar este mensaje: '
        f'tu contraseña actual sigue siendo válida.\n\n'
        f'— {NOMBRE_PROYECTO}'
    )
    mensaje = MIMEText(cuerpo, 'plain', 'utf-8')
    mensaje['Subject'] = f'Código de verificación · {NOMBRE_PROYECTO}'
    mensaje['From'] = GMAIL_USUARIO
    mensaje['To'] = destinatario

    with smtplib.SMTP('smtp.gmail.com', 587, timeout=15) as servidor:
        servidor.starttls()
        servidor.login(GMAIL_USUARIO, GMAIL_APP_PASSWORD)
        servidor.sendmail(GMAIL_USUARIO, [destinatario], mensaje.as_string())


@app.context_processor
def inyectar_datos_globales():
    """Pone nombre_proyecto, lema_proyecto y la vigencia del código de
    recuperación disponibles en cualquier template."""
    return {
        'nombre_proyecto': NOMBRE_PROYECTO,
        'lema_proyecto': LEMA_PROYECTO,
        'vigencia_minutos': CODIGO_VIGENCIA_MINUTOS,
    }


# ------------------------------------------------------------------
# 1) BASE DE DATOS
# ------------------------------------------------------------------

def get_db():
    """Abre una conexión nueva a la base de datos SQLite."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # permite leer columnas por nombre: fila['marca']
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def init_db():
    """Crea las tablas (si no existen todavía) a partir de schema.sql."""
    conn = get_db()
    with open(os.path.join(BASE_DIR, 'schema.sql'), 'r', encoding='utf-8') as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()


def migrar_bd():
    """Añade columnas nuevas (correo, código de recuperación) a bases de
    datos creadas con una versión anterior de schema.sql, sin borrar nada
    de lo que ya exista. Si la columna ya está, no hace nada."""
    conn = get_db()
    columnas_existentes = {fila['name'] for fila in conn.execute('PRAGMA table_info(usuarios)')}

    columnas_nuevas = {
        'correo': 'TEXT',
        'codigo_recuperacion': 'TEXT',
        'codigo_expiracion': 'TIMESTAMP',
    }
    for columna, tipo in columnas_nuevas.items():
        if columna not in columnas_existentes:
            conn.execute(f'ALTER TABLE usuarios ADD COLUMN {columna} {tipo}')

    conn.commit()
    conn.close()


# ------------------------------------------------------------------
# 2) REGISTRO DE ACTIVIDAD DE USUARIOS
# ------------------------------------------------------------------

def registrar_actividad(usuario_id, accion, tabla_afectada=None, registro_id=None, detalle=None):
    """Guarda en la tabla 'actividad' qué usuario hizo qué acción y cuándo."""
    conn = get_db()
    conn.execute(
        '''INSERT INTO actividad (usuario_id, accion, tabla_afectada, registro_id, detalle)
           VALUES (?, ?, ?, ?, ?)''',
        (usuario_id, accion, tabla_afectada, registro_id, detalle)
    )
    conn.commit()
    conn.close()


def login_requerido(vista):
    """Decorador: bloquea el acceso a una ruta si no hay sesión iniciada."""
    @wraps(vista)
    def envoltorio(*args, **kwargs):
        if 'usuario_id' not in session:
            if request.path.startswith('/api/'):
                return jsonify({'error': 'No has iniciado sesión'}), 401
            return redirect(url_for('login'))
        return vista(*args, **kwargs)
    return envoltorio


def admin_requerido(vista):
    """Como login_requerido, pero además exige que el usuario tenga rol 'admin'.
    Se usa en todo lo que modifica datos: alta/baja de equipos y de cuentas."""
    @wraps(vista)
    def envoltorio(*args, **kwargs):
        if 'usuario_id' not in session:
            if request.path.startswith('/api/'):
                return jsonify({'error': 'No has iniciado sesión'}), 401
            return redirect(url_for('login'))
        if session.get('rol') != 'admin':
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Necesitas una cuenta de administrador para hacer esto'}), 403
            return redirect(url_for('index'))
        return vista(*args, **kwargs)
    return envoltorio


def edicion_o_admin_requerido(vista):
    """Como login_requerido, pero exige rol 'admin' o 'editor'.
    Se usa solo para EDITAR (PUT) computadores: crear y eliminar
    equipos, y todo lo de /usuarios, se queda exclusivo de 'admin'."""
    @wraps(vista)
    def envoltorio(*args, **kwargs):
        if 'usuario_id' not in session:
            if request.path.startswith('/api/'):
                return jsonify({'error': 'No has iniciado sesión'}), 401
            return redirect(url_for('login'))
        if session.get('rol') not in ('admin', 'editor'):
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Necesitas una cuenta de administrador o de edición para hacer esto'}), 403
            return redirect(url_for('index'))
        return vista(*args, **kwargs)
    return envoltorio


# ------------------------------------------------------------------
# 4) RUTAS DE PÁGINAS (HTML)
# ------------------------------------------------------------------

@app.route('/')
@login_requerido
def index():
    """Dashboard: listado de todos los computadores de la sala."""
    return render_template('index.html', usuario=session.get('nombre_completo'), rol=session.get('rol'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        nombre_usuario = request.form.get('nombre_usuario', '').strip()
        contrasena = request.form.get('contrasena', '')

        conn = get_db()
        usuario = conn.execute(
            'SELECT * FROM usuarios WHERE nombre_usuario = ?', (nombre_usuario,)
        ).fetchone()
        conn.close()

        if usuario and check_password_hash(usuario['contrasena'], contrasena):
            session['usuario_id'] = usuario['id']
            session['nombre_completo'] = usuario['nombre_completo']
            session['rol'] = usuario['rol']
            registrar_actividad(usuario['id'], 'INICIO_SESION',
                                 detalle=f'{nombre_usuario} inició sesión')
            return redirect(url_for('index'))

        return render_template('login.html', error='Usuario o contraseña incorrectos')

    exito = None
    if request.args.get('recuperado'):
        exito = 'Tu contraseña se actualizó correctamente. Ya puedes iniciar sesión.'
    return render_template('login.html', exito=exito)


@app.route('/usuarios')
@admin_requerido
def usuarios():
    """Gestión de cuentas: añadir o eliminar usuarios. Solo para administradores."""
    return render_template('usuarios.html', rol=session.get('rol'), usuario_actual_id=session.get('usuario_id'))


@app.route('/logout')
def logout():
    if 'usuario_id' in session:
        registrar_actividad(session['usuario_id'], 'CIERRE_SESION')
    session.clear()
    return redirect(url_for('login'))


# ------------------------------------------------------------------
# 5) RECUPERACIÓN DE CONTRASEÑA (verificación por código a Gmail)
# ------------------------------------------------------------------

@app.route('/recuperar', methods=['GET', 'POST'])
def recuperar_contrasena():
    """Paso 1: el usuario escribe su usuario o su correo. Si existe y
    tiene un correo asociado, le enviamos un código de 6 dígitos."""
    if request.method == 'POST':
        identificador = request.form.get('identificador', '').strip()

        conn = get_db()
        usuario = conn.execute(
            'SELECT * FROM usuarios WHERE nombre_usuario = ? OR correo = ?',
            (identificador, identificador)
        ).fetchone()

        # Mensaje genérico a propósito: no revela si la cuenta existe o no.
        mensaje = ('Si los datos corresponden a una cuenta con correo registrado, '
                    'te enviamos un código de verificación.')

        if usuario is None or not usuario['correo']:
            conn.close()
            return render_template('recuperar.html', mensaje=mensaje)

        codigo = f'{secrets.randbelow(1_000_000):06d}'
        expiracion = datetime.now() + timedelta(minutes=CODIGO_VIGENCIA_MINUTOS)
        conn.execute(
            'UPDATE usuarios SET codigo_recuperacion = ?, codigo_expiracion = ? WHERE id = ?',
            (codigo, expiracion.isoformat(sep=' '), usuario['id'])
        )
        conn.commit()

        try:
            enviar_codigo_por_correo(usuario['correo'], codigo)
        except Exception:
            conn.close()
            return render_template(
                'recuperar.html',
                error='No se pudo enviar el código por correo. Avisa a un administrador '
                      '(revisa que GMAIL_USUARIO y GMAIL_APP_PASSWORD estén configurados).'
            )

        conn.close()
        session['recuperacion_usuario_id'] = usuario['id']
        registrar_actividad(usuario['id'], 'SOLICITAR_RECUPERACION', 'usuarios', usuario['id'],
                             'Solicitó un código de recuperación de contraseña')
        return redirect(url_for('verificar_codigo'))

    return render_template('recuperar.html')


@app.route('/recuperar/verificar', methods=['GET', 'POST'])
def verificar_codigo():
    """Paso 2: el usuario escribe el código que le llegó al correo y su
    contraseña nueva. Solo se puede llegar aquí tras pasar por /recuperar."""
    usuario_id = session.get('recuperacion_usuario_id')
    if not usuario_id:
        return redirect(url_for('recuperar_contrasena'))

    if request.method == 'POST':
        codigo_ingresado = request.form.get('codigo', '').strip()
        nueva_contrasena = request.form.get('nueva_contrasena', '')
        confirmar_contrasena = request.form.get('confirmar_contrasena', '')

        conn = get_db()
        usuario = conn.execute('SELECT * FROM usuarios WHERE id = ?', (usuario_id,)).fetchone()

        error = None
        if usuario is None:
            error = 'La sesión de recuperación expiró. Solicita un nuevo código.'
        elif not usuario['codigo_recuperacion'] or codigo_ingresado != usuario['codigo_recuperacion']:
            error = 'El código ingresado no es correcto.'
        elif not usuario['codigo_expiracion'] or datetime.fromisoformat(usuario['codigo_expiracion']) < datetime.now():
            error = 'El código venció. Vuelve a solicitar uno nuevo.'
        elif len(nueva_contrasena) < 4:
            error = 'La contraseña nueva debe tener al menos 4 caracteres.'
        elif nueva_contrasena != confirmar_contrasena:
            error = 'Las dos contraseñas no coinciden.'

        if error:
            conn.close()
            return render_template('verificar_codigo.html', error=error)

        conn.execute(
            '''UPDATE usuarios
               SET contrasena = ?, codigo_recuperacion = NULL, codigo_expiracion = NULL
               WHERE id = ?''',
            (generate_password_hash(nueva_contrasena), usuario_id)
        )
        conn.commit()
        conn.close()

        registrar_actividad(usuario_id, 'RESTABLECER_CONTRASENA', 'usuarios', usuario_id,
                             'Restableció su contraseña mediante el código enviado por correo')

        session.pop('recuperacion_usuario_id', None)
        return redirect(url_for('login', recuperado='1'))

    return render_template('verificar_codigo.html')


@app.route('/recuperar/cancelar')
def cancelar_recuperacion():
    session.pop('recuperacion_usuario_id', None)
    return redirect(url_for('recuperar_contrasena'))


@app.route('/computador/<int:computador_id>')
@login_requerido
def computador_detalle(computador_id):
    """La 'ficha' individual de un computador: número, marca, serial, estado y mantenimiento."""
    return render_template('computador_detalle.html', computador_id=computador_id, rol=session.get('rol'))


# ------------------------------------------------------------------
# 6) API REST DE COMPUTADORES  ->  usada por static/js/*.js con fetch()
# ------------------------------------------------------------------

@app.route('/api/computadores', methods=['GET'])
@login_requerido
def api_listar_computadores():
    conn = get_db()
    filas = conn.execute('SELECT * FROM computadores ORDER BY numero_computador').fetchall()
    conn.close()
    return jsonify([dict(fila) for fila in filas])


@app.route('/api/computadores/<int:computador_id>', methods=['GET'])
@login_requerido
def api_obtener_computador(computador_id):
    conn = get_db()
    fila = conn.execute('SELECT * FROM computadores WHERE id = ?', (computador_id,)).fetchone()
    conn.close()

    if fila is None:
        return jsonify({'error': 'Computador no encontrado'}), 404

    registrar_actividad(session['usuario_id'], 'CONSULTAR', 'computadores', computador_id)
    return jsonify(dict(fila))


@app.route('/api/computadores', methods=['POST'])
@admin_requerido
def api_crear_computador():
    datos = request.get_json(silent=True) or {}

    for campo in ('numero_computador', 'marca', 'serial', 'estado'):
        if not str(datos.get(campo, '')).strip():
            return jsonify({'error': f'El campo "{campo}" es obligatorio'}), 400

    conn = get_db()
    try:
        cursor = conn.execute(
            '''INSERT INTO computadores (numero_computador, marca, serial, estado, ficha_mantenimiento)
               VALUES (?, ?, ?, ?, ?)''',
            (datos['numero_computador'].strip(), datos['marca'].strip(), datos['serial'].strip(),
             datos['estado'], datos.get('ficha_mantenimiento', '').strip())
        )
        conn.commit()
        nuevo_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'error': 'Ya existe un computador con ese número o ese serial'}), 400
    conn.close()

    registrar_actividad(session['usuario_id'], 'CREAR', 'computadores', nuevo_id,
                         f'Registró el computador {datos["numero_computador"]}')
    return jsonify({'mensaje': 'Computador registrado correctamente', 'id': nuevo_id}), 201


@app.route('/api/computadores/<int:computador_id>', methods=['PUT'])
@edicion_o_admin_requerido
def api_actualizar_computador(computador_id):
    datos = request.get_json(silent=True) or {}

    conn = get_db()
    existente = conn.execute('SELECT * FROM computadores WHERE id = ?', (computador_id,)).fetchone()
    if existente is None:
        conn.close()
        return jsonify({'error': 'Computador no encontrado'}), 404

    try:
        conn.execute(
            '''UPDATE computadores
               SET numero_computador = ?, marca = ?, serial = ?, estado = ?, ficha_mantenimiento = ?
               WHERE id = ?''',
            (
                datos.get('numero_computador', existente['numero_computador']).strip(),
                datos.get('marca', existente['marca']).strip(),
                datos.get('serial', existente['serial']).strip(),
                datos.get('estado', existente['estado']),
                datos.get('ficha_mantenimiento', existente['ficha_mantenimiento'] or '').strip(),
                computador_id
            )
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'error': 'Ese número o serial ya lo usa otro computador'}), 400
    conn.close()

    registrar_actividad(session['usuario_id'], 'ACTUALIZAR', 'computadores', computador_id,
                         f'Actualizó el computador #{computador_id}')
    return jsonify({'mensaje': 'Computador actualizado correctamente'})


@app.route('/api/computadores/<int:computador_id>', methods=['DELETE'])
@admin_requerido
def api_eliminar_computador(computador_id):
    conn = get_db()
    existente = conn.execute('SELECT * FROM computadores WHERE id = ?', (computador_id,)).fetchone()
    if existente is None:
        conn.close()
        return jsonify({'error': 'Computador no encontrado'}), 404

    conn.execute('DELETE FROM computadores WHERE id = ?', (computador_id,))
    conn.commit()
    conn.close()

    registrar_actividad(session['usuario_id'], 'ELIMINAR', 'computadores', computador_id,
                         f'Eliminó el computador {existente["numero_computador"]}')
    return jsonify({'mensaje': 'Computador eliminado correctamente'})


# ------------------------------------------------------------------
# 7) API REST DE USUARIOS  ->  gestión de cuentas, solo administradores
# ------------------------------------------------------------------

@app.route('/api/usuarios', methods=['GET'])
@admin_requerido
def api_listar_usuarios():
    conn = get_db()
    filas = conn.execute(
        'SELECT id, nombre_usuario, nombre_completo, correo, rol, fecha_creacion FROM usuarios ORDER BY fecha_creacion'
    ).fetchall()
    conn.close()
    return jsonify([dict(fila) for fila in filas])


@app.route('/api/usuarios', methods=['POST'])
@admin_requerido
def api_crear_usuario():
    datos = request.get_json(silent=True) or {}
    nombre_usuario = str(datos.get('nombre_usuario', '')).strip()
    nombre_completo = str(datos.get('nombre_completo', '')).strip()
    correo = str(datos.get('correo', '')).strip()
    contrasena = str(datos.get('contrasena', ''))
    rol = datos.get('rol') if datos.get('rol') in ('admin', 'editor', 'consulta') else 'consulta'

    if not nombre_usuario or not nombre_completo or not contrasena:
        return jsonify({'error': 'Usuario, nombre completo y contraseña son obligatorios'}), 400
    if len(contrasena) < 4:
        return jsonify({'error': 'La contraseña debe tener al menos 4 caracteres'}), 400
    if not correo or '@' not in correo:
        return jsonify({'error': 'El correo es obligatorio y se usa para recuperar la contraseña'}), 400

    conn = get_db()
    existe = conn.execute('SELECT id FROM usuarios WHERE nombre_usuario = ?', (nombre_usuario,)).fetchone()
    if existe:
        conn.close()
        return jsonify({'error': 'Ese nombre de usuario ya existe'}), 400

    correo_en_uso = conn.execute('SELECT id FROM usuarios WHERE correo = ?', (correo,)).fetchone()
    if correo_en_uso:
        conn.close()
        return jsonify({'error': 'Ese correo ya está en uso por otra cuenta'}), 400

    cursor = conn.execute(
        'INSERT INTO usuarios (nombre_usuario, contrasena, nombre_completo, correo, rol) VALUES (?, ?, ?, ?, ?)',
        (nombre_usuario, generate_password_hash(contrasena), nombre_completo, correo, rol)
    )
    conn.commit()
    nuevo_id = cursor.lastrowid
    conn.close()

    registrar_actividad(session['usuario_id'], 'CREAR', 'usuarios', nuevo_id,
                         f'Creó la cuenta {nombre_usuario} (rol: {rol})')
    return jsonify({'mensaje': 'Cuenta creada correctamente', 'id': nuevo_id}), 201


@app.route('/api/usuarios/<int:usuario_id>', methods=['PUT'])
@admin_requerido
def api_actualizar_usuario(usuario_id):
    """Edita nombre completo, correo y rol de una cuenta existente.
    No cambia el nombre de usuario ni la contraseña (para eso está
    /recuperar). Útil sobre todo para registrar el correo de Gmail
    de una cuenta creada antes de tener esta función."""
    datos = request.get_json(silent=True) or {}

    conn = get_db()
    existente = conn.execute('SELECT * FROM usuarios WHERE id = ?', (usuario_id,)).fetchone()
    if existente is None:
        conn.close()
        return jsonify({'error': 'Cuenta no encontrada'}), 404

    nombre_completo = str(datos.get('nombre_completo', existente['nombre_completo'])).strip()
    correo = str(datos.get('correo', existente['correo'] or '')).strip()
    rol = datos.get('rol') if datos.get('rol') in ('admin', 'editor', 'consulta') else existente['rol']

    if not nombre_completo:
        conn.close()
        return jsonify({'error': 'El nombre completo no puede quedar vacío'}), 400
    if not correo or '@' not in correo:
        conn.close()
        return jsonify({'error': 'El correo es obligatorio y se usa para recuperar la contraseña'}), 400

    if existente['rol'] == 'admin' and rol != 'admin':
        total_admins = conn.execute("SELECT COUNT(*) AS c FROM usuarios WHERE rol = 'admin'").fetchone()['c']
        if total_admins <= 1:
            conn.close()
            return jsonify({'error': 'No puedes quitarle el rol de administrador al último admin que queda'}), 400

    correo_en_uso = conn.execute(
        'SELECT id FROM usuarios WHERE correo = ? AND id != ?', (correo, usuario_id)
    ).fetchone()
    if correo_en_uso:
        conn.close()
        return jsonify({'error': 'Ese correo ya está en uso por otra cuenta'}), 400

    conn.execute(
        'UPDATE usuarios SET nombre_completo = ?, correo = ?, rol = ? WHERE id = ?',
        (nombre_completo, correo, rol, usuario_id)
    )
    conn.commit()
    conn.close()

    registrar_actividad(session['usuario_id'], 'ACTUALIZAR', 'usuarios', usuario_id,
                         f'Editó la cuenta {existente["nombre_usuario"]}')
    return jsonify({'mensaje': 'Cuenta actualizada correctamente'})


@app.route('/api/usuarios/<int:usuario_id>', methods=['DELETE'])
@admin_requerido
def api_eliminar_usuario(usuario_id):
    if usuario_id == session['usuario_id']:
        return jsonify({'error': 'No puedes eliminar tu propia cuenta mientras tienes sesión iniciada con ella'}), 400

    conn = get_db()
    objetivo = conn.execute('SELECT * FROM usuarios WHERE id = ?', (usuario_id,)).fetchone()
    if objetivo is None:
        conn.close()
        return jsonify({'error': 'Cuenta no encontrada'}), 404

    if objetivo['rol'] == 'admin':
        total_admins = conn.execute("SELECT COUNT(*) AS c FROM usuarios WHERE rol = 'admin'").fetchone()['c']
        if total_admins <= 1:
            conn.close()
            return jsonify({'error': 'No puedes eliminar al último administrador que queda'}), 400

    conn.execute('DELETE FROM usuarios WHERE id = ?', (usuario_id,))
    conn.commit()
    conn.close()

    registrar_actividad(session['usuario_id'], 'ELIMINAR', 'usuarios', usuario_id,
                         f'Eliminó la cuenta {objetivo["nombre_usuario"]}')
    return jsonify({'mensaje': 'Cuenta eliminada correctamente'})


def sembrar_administradores():
    """Crea las 2 cuentas administrativas iniciales, solo si todavía no existe
    ningún usuario en la base de datos (para no duplicarlas en cada arranque)."""
    conn = get_db()
    total = conn.execute('SELECT COUNT(*) AS c FROM usuarios').fetchone()['c']
    if total == 0:
        iniciales = [
            ('admin1', 'Phronesis2026!', 'Administrador 1', 'admin'),
            ('admin2', 'Phronesis2026#', 'Administrador 2', 'admin'),
        ]
        for nombre_usuario, contrasena, nombre_completo, rol in iniciales:
            # El correo queda vacío: entra en /usuarios y pulsa "Editar" en
            # cada cuenta para asignarle un Gmail real, así /recuperar
            # puede enviarle un código si algún día olvida la contraseña.
            conn.execute(
                'INSERT INTO usuarios (nombre_usuario, contrasena, nombre_completo, correo, rol) VALUES (?, ?, ?, ?, ?)',
                (nombre_usuario, generate_password_hash(contrasena), nombre_completo, None, rol)
            )
        conn.commit()
        print('Cuentas administrativas creadas: admin1 / admin2 (cambia sus contraseñas y '
              'asígnales un correo desde "Gestión de usuarios" cuanto antes)')
    conn.close()


# ------------------------------------------------------------------
# PUNTO DE ENTRADA
# ------------------------------------------------------------------

if __name__ == '__main__':
    init_db()  # crea la BD y las tablas la primera vez que se ejecuta
    migrar_bd()  # añade columnas nuevas (correo, código de recuperación) si faltan
    sembrar_administradores()  # crea admin1 y admin2 si la BD está recién creada
    if not GMAIL_USUARIO or not GMAIL_APP_PASSWORD:
        print('Aviso: GMAIL_USUARIO / GMAIL_APP_PASSWORD no están configurados; '
              '/recuperar no podrá enviar correos hasta que los definas (ver app.py).')
    app.run(debug=True, port=5000)
