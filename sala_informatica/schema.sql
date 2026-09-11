-- ============================================================
--  BASE DE DATOS: Sistema de Gestión de la Sala de Informática
-- ============================================================
-- Motor: SQLite (no necesita instalación de servidor de BD,
-- ideal para un proyecto que corre en local sin coste).

-- Tabla de USUARIOS del sistema (quienes acceden a gestionar la sala)
CREATE TABLE IF NOT EXISTS usuarios (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_usuario       TEXT NOT NULL UNIQUE,      -- login, no se puede repetir
    contrasena           TEXT NOT NULL,             -- se guarda con hash, nunca en texto plano
    nombre_completo      TEXT NOT NULL,
    correo               TEXT,                      -- correo (Gmail) para recuperar la contraseña
    rol                  TEXT NOT NULL DEFAULT 'consulta',  -- 'admin' / 'editor' / 'consulta'
    codigo_recuperacion  TEXT,                      -- código de verificación temporal (recuperar contraseña)
    codigo_expiracion    TIMESTAMP,                 -- cuándo vence ese código
    fecha_creacion       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de COMPUTADORES de la sala de informática
CREATE TABLE IF NOT EXISTS computadores (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    numero_computador    TEXT NOT NULL UNIQUE,     -- ej: "PC-01"
    marca                TEXT NOT NULL,
    serial               TEXT NOT NULL UNIQUE,
    estado               TEXT NOT NULL DEFAULT 'Activo',
                         -- valores usados: Activo / En mantenimiento / Dañado / De baja
    ficha_mantenimiento  TEXT,                      -- notas/historial de mantenimiento
    fecha_registro       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de ACTIVIDAD: registra qué usuario hizo qué acción y cuándo
-- (esto es el "guardar la información de la actividad de los usuarios")
CREATE TABLE IF NOT EXISTS actividad (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id      INTEGER,            -- puede quedar NULL si esa cuenta se elimina después
    accion          TEXT NOT NULL,      -- CREAR / CONSULTAR / ACTUALIZAR / ELIMINAR / INICIO_SESION / REGISTRO
    tabla_afectada  TEXT,               -- normalmente "computadores" o "usuarios"
    registro_id     INTEGER,            -- id del computador/usuario afectado (si aplica)
    detalle         TEXT,
    fecha_hora      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios (id) ON DELETE SET NULL
);
