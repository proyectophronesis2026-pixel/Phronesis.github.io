# Phronesis · Knowledge Systems

Sistema de gestión de la sala de informática — proyecto de
aprendizaje, Sistemas Teleinformáticos.
Aplicación web que permite gestionar (crear, consultar, actualizar,
eliminar) los computadores de una sala de informática, con tres
roles de usuario (administrador, edición y consulta), recuperación
de contraseña por código enviado a Gmail, y un registro de
actividad de cada acción realizada.

## Tecnologías utilizadas

| Capa                | Tecnología                              |
|---------------------|------------------------------------------|
| Backend              | Python 3 + Flask                        |
| Base de datos        | SQLite (un solo archivo, sin instalar servidor) |
| Frontend (pantallas) | HTML5 + CSS3                            |
| Frontend (interacción) | JavaScript (fetch API, sin librerías) |

Se usa SQLite (en vez de MySQL/PostgreSQL) a propósito: no necesita
instalar ningún servidor de base de datos aparte, todo corre en
local con un solo archivo `.db`, sin ningún coste.

## Cuentas de acceso

**Ya no existe registro público.** Las cuentas solo las crea un
administrador desde la pantalla "Gestión de usuarios". Al arrancar
la aplicación por primera vez (con la base de datos vacía) se crean
automáticamente 2 cuentas administrativas:

| Usuario  | Contraseña        |
|----------|-------------------|
| `admin1` | `Phronesis2026!`  |
| `admin2` | `Phronesis2026#`  |

**Cambia estas contraseñas cuanto antes** (inicia sesión, crea tu
propia cuenta admin desde "Gestión de usuarios" y luego elimina
estas dos de ejemplo).

Hay tres roles:
- **admin** — todo: crear/editar/eliminar computadores, y
  añadir/editar/eliminar cuentas de usuario.
- **editor** ("Edición") — puede editar la ficha de un computador
  (incluido su estado), pero **no puede eliminarlo** ni crear
  equipos nuevos, y no entra a "Gestión de usuarios".
- **consulta** — solo puede iniciar sesión y ver los computadores
  y su ficha; no ve los botones de añadir, editar ni eliminar.

Cada cuenta necesita un **correo** (recomendado: un Gmail) para
poder usar "¿Olvidaste tu contraseña?" desde el login — ver la
sección de recuperación de contraseña más abajo.

## Estructura del proyecto

```
sala_informatica/
├── app.py                       # Backend Flask: rutas y API REST
├── schema.sql                   # Diseño de las tablas (usuarios, computadores, actividad)
├── requirements.txt             # Dependencias (solo Flask)
├── sala_informatica.db          # Se crea sola la primera vez que ejecutas app.py
├── templates/                   # Pantallas HTML (Jinja2)
│   ├── base.html                 # Cabecera común (fuentes, CSS)
│   ├── login.html                 # Iniciar sesión
│   ├── recuperar.html              # Paso 1: pedir usuario/correo para recuperar contraseña
│   ├── verificar_codigo.html       # Paso 2: ingresar el código y la contraseña nueva
│   ├── index.html                  # Listado de computadores (dashboard)
│   ├── computador_detalle.html     # Ficha individual de un computador
│   └── usuarios.html               # Gestión de cuentas (solo admin)
└── static/
    ├── css/style.css             # Estilos de toda la app
    └── js/
        ├── dashboard.js           # Botones y formulario del listado
        ├── detalle.js              # Botones y formulario de la ficha individual
        └── usuarios.js              # Botones y formulario de gestión de usuarios
```

## Diseño de la base de datos

**usuarios** — quién puede entrar al sistema
`id · nombre_usuario · contrasena (con hash) · nombre_completo · correo · rol · codigo_recuperacion · codigo_expiracion · fecha_creacion`
(`rol` es `'admin'`, `'editor'` o `'consulta'`. `codigo_recuperacion`
y `codigo_expiracion` solo se llenan mientras hay una recuperación
de contraseña en curso; se borran en cuanto se usa el código.)

**computadores** — el inventario de la sala
`id · numero_computador · marca · serial · estado · ficha_mantenimiento · fecha_registro`

**actividad** — auditoría: qué usuario hizo qué acción y cuándo
`id · usuario_id (FK, puede ser NULL) · accion · tabla_afectada · registro_id · detalle · fecha_hora`

Cada vez que alguien crea, consulta, actualiza o elimina un
computador o una cuenta (o inicia sesión), se inserta una fila en
`actividad`. Si esa cuenta se elimina más adelante, la fila de
actividad se conserva (con `usuario_id` en NULL) para no perder el
historial.

## Cómo ejecutarlo en Visual Studio Code

**1. Requisito previo:** tener Python 3 instalado. Comprueba en una
terminal (en Windows a veces el comando es `py` en vez de `python`):
```
python --version
```

**2. Abre la carpeta del proyecto en VS Code**
`Archivo → Abrir carpeta…` y selecciona la carpeta `sala_informatica`.

**3. Abre una terminal integrada**
`Terminal → Nueva terminal` (o `` Ctrl+ñ `` / `` Ctrl+` ``).

**4. (Recomendado) crea un entorno virtual**
```
python -m venv venv
```
Actívalo:
- Windows: `venv\Scripts\activate`
- Mac/Linux: `source venv/bin/activate`

**5. Instala las dependencias**
```
pip install -r requirements.txt
```

**6. Ejecuta la aplicación**
```
python app.py
```
La primera vez creará automáticamente `sala_informatica.db` con las
tablas y las 2 cuentas admin de ejemplo (ver arriba).

**7. Ábrela en el navegador**
Verás en la terminal un mensaje como
`Running on http://127.0.0.1:5000`. Abre esa dirección
(`http://localhost:5000`) en tu navegador.

**8. Para probarla**
1. Inicia sesión con `admin1` / `Phronesis2026!`.
2. Pulsa «+ Añadir equipo» y crea tu primer computador.
3. Entra a «Gestión de usuarios» y crea una cuenta de prueba con
   rol "consulta", para ver cómo cambia la interfaz con ese rol.
4. Pulsa «Ver ficha» en un equipo para entrar a su pantalla
   individual, editarlo o eliminarlo (solo como admin).

Para parar el servidor, vuelve a la terminal y pulsa `Ctrl+C`.

ℹ️ Si ya tenías un archivo `sala_informatica.db` de una versión
anterior (sin roles de edición ni recuperación de contraseña), **no
hace falta borrarlo**: al ejecutar `app.py`, `migrar_bd()` añade
solas las columnas nuevas (`correo`, `codigo_recuperacion`,
`codigo_expiracion`) sin borrar los computadores ni las cuentas que
ya tenías. Eso sí, esas cuentas antiguas quedarán sin correo hasta
que entres a "Gestión de usuarios" y se lo asignes con "Editar".

## Configurar el envío del código de recuperación por Gmail

"¿Olvidaste tu contraseña?" (desde el login) funciona así: pides tu
usuario o correo → la app genera un código de 6 dígitos → te lo
envía por correo con una cuenta de Gmail → lo escribes junto con tu
contraseña nueva. **El código nunca se muestra en pantalla ni se
imprime en la terminal**, solo llega al correo de la cuenta.

**Este proyecto ya trae un archivo `.env`** (en la misma carpeta que
`app.py`) con el Gmail remitente `prhonesis387@gmail.com` puesto.
`app.py` lo lee automáticamente con `load_dotenv()` al arrancar, así
que no tienes que definir nada a mano — solo instala
`python-dotenv` (ya está en `requirements.txt`) y ejecuta la app.

⚠️ **Importante:** la contraseña que quedó en `.env` es la que me
diste, que tiene forma de contraseña normal de la cuenta, **no** de
"contraseña de aplicación". Gmail exige una contraseña de aplicación
para enviar correos por SMTP (así seas tú mismo el dueño de la
cuenta) — con la contraseña normal, muy probablemente el envío
fallará con un error de autenticación. Para arreglarlo:

1. Entra a la cuenta `prhonesis387@gmail.com` y activa la
   verificación en dos pasos: <https://myaccount.google.com/security>
2. Ve a <https://myaccount.google.com/apppasswords> y crea una
   "contraseña de aplicación" (elige "Otra", ponle un nombre como
   "Phronesis"). Google te da un código de 16 letras.
3. Abre el archivo `.env` con cualquier editor de texto y reemplaza
   el valor de `GMAIL_APP_PASSWORD` por ese código de 16 letras
   (déjalo sin espacios ni comillas). Guarda el archivo.
4. Vuelve a ejecutar `python app.py`.

⚠️ **No subas el archivo `.env` a ningún repositorio, Classroom o
carpeta compartida** — quien lo tenga puede enviar correos desde esa
cuenta de Gmail. Ya está agregado a `.gitignore` para que Git no lo
suba si usas control de versiones. Y como esa contraseña se escribió
en este chat, te recomiendo cambiarla desde la configuración de la
cuenta de Google en cuanto puedas, y usar solo la contraseña de
aplicación de aquí en adelante.

Si por algún motivo prefieres no usar `.env`, también puedes definir
las mismas variables directamente en la terminal antes de ejecutar
la app (`load_dotenv()` no sobrescribe variables que ya existan):

**Windows (PowerShell)**
```
$env:GMAIL_USUARIO="tu_correo@gmail.com"
$env:GMAIL_APP_PASSWORD="xxxxxxxxxxxxxxxx"
python app.py
```

**Mac / Linux**
```
export GMAIL_USUARIO="tu_correo@gmail.com"
export GMAIL_APP_PASSWORD="xxxxxxxxxxxxxxxx"
python app.py
```

Por último, asegúrate de que cada cuenta a la que le quieras poder
recuperar la contraseña tenga un correo guardado: entra a "Gestión
de usuarios" → botón **"Editar"** en esa cuenta → escribe su Gmail
en el campo "Correo" y guarda. Ese es el "espacio" para asignarle un
Gmail a cada cuenta — ya viene incluido en esta versión, tanto al
crear una cuenta nueva como al editar una existente (útil para
admin1 y admin2, que se crean sin correo).

Mientras `GMAIL_USUARIO` / `GMAIL_APP_PASSWORD` no estén definidas o
sean inválidas, verás un aviso en la terminal al arrancar, y
`/recuperar` mostrará un mensaje de error (sin revelar el código)
indicando que el envío de correo no está configurado.

**Sí, se puede enviar a cualquier Gmail** (o a cualquier correo en
general): el remitente tiene que ser una cuenta de Gmail con
contraseña de aplicación, pero el destinatario (`usuario['correo']`)
puede ser cualquier dirección de correo válida.

## Cosas para tener en cuenta al presentarlo

- Las contraseñas no se guardan en texto plano: se guarda un
  *hash* (`werkzeug.security`), así que aunque alguien abra el
  archivo `.db` no puede leer la contraseña original.
- Todas las rutas comprueban sesión iniciada (`@login_requerido`);
  las de escritura (crear/editar/eliminar equipos, gestionar
  cuentas) además exigen rol admin (`@admin_requerido`). Un intento
  de acceso sin permiso responde 403 (API) o redirige (páginas).
- No puedes eliminar tu propia cuenta ni al último administrador
  que quede, para no bloquear el sistema por accidente.
- El "estado" del computador es uno de cuatro valores fijos
  (Activo, En mantenimiento, Dañado, De baja) para evitar errores
  de escritura y poder mostrarlo siempre con el mismo color.

## Posibles mejoras (si te sobra tiempo)

- Añadir un buscador/filtro por estado o marca en el dashboard.
- Mostrar en el dashboard una pantalla aparte con el historial de
  la tabla `actividad` (quién hizo qué y cuándo).
- Permitir que cada usuario cambie su propia contraseña desde la
  aplicación (por ahora solo un admin puede crear/eliminar cuentas).
