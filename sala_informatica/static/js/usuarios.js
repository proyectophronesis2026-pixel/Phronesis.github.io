/* ============================================================
   usuarios.js
   Lógica de la pantalla de gestión de usuarios (usuarios.html):
   - Pide la lista de cuentas a la API (fetch GET)
   - Dibuja una tarjeta por cada una
   - Controla el formulario modal para crear una cuenta (fetch POST)
   - Controla el botón "Eliminar cuenta" de cada tarjeta (fetch DELETE)
   Esta pantalla solo la puede abrir un administrador (lo protege app.py).
   ============================================================ */

const grid = document.getElementById('grid-usuarios');
const contador = document.getElementById('contador-usuarios');
const mensajeError = document.getElementById('mensaje-error');
const plantillaUsuario = document.getElementById('plantilla-usuario');

const modal = document.getElementById('modal-nueva-cuenta');
const formNuevaCuenta = document.getElementById('form-nueva-cuenta');
const modalError = document.getElementById('modal-error');

const modalEditar = document.getElementById('modal-editar-cuenta');
const formEditarCuenta = document.getElementById('form-editar-cuenta');
const modalEditarError = document.getElementById('modal-editar-error');

const ETIQUETAS_ROL = {
    admin: 'Administrador',
    editor: 'Edición',
    consulta: 'Consulta',
};
const CLASES_ROL = {
    admin: 'sello--activo',
    editor: 'sello--en-mantenimiento',
    consulta: 'sello--de-baja',
};

function mostrarError(texto) {
    mensajeError.textContent = texto;
    mensajeError.classList.remove('oculto');
}

function ocultarError() {
    mensajeError.classList.add('oculto');
}

// ---------- Cargar y dibujar la lista ----------

async function cargarUsuarios() {
    ocultarError();
    try {
        const respuesta = await fetch('/api/usuarios');
        if (!respuesta.ok) throw new Error('No se pudo obtener la lista de cuentas');

        const usuarios = await respuesta.json();
        dibujarLista(usuarios);
    } catch (error) {
        mostrarError('Error al cargar las cuentas: ' + error.message);
    }
}

function dibujarLista(usuarios) {
    grid.innerHTML = '';

    contador.textContent = usuarios.length === 1
        ? '1 cuenta registrada'
        : `${usuarios.length} cuentas registradas`;

    usuarios.forEach((usuario) => grid.appendChild(crearTarjeta(usuario)));
}

function crearTarjeta(usuario) {
    const nodo = plantillaUsuario.content.cloneNode(true);

    nodo.querySelector('[data-campo="nombre_usuario"]').textContent = '@' + usuario.nombre_usuario;
    nodo.querySelector('[data-campo="nombre_completo"]').textContent = usuario.nombre_completo;
    nodo.querySelector('[data-campo="correo"]').textContent = usuario.correo || 'Sin correo registrado';
    nodo.querySelector('[data-campo="fecha_creacion"]').textContent = 'Desde ' + usuario.fecha_creacion;

    const sello = nodo.querySelector('[data-campo="rol"]');
    sello.textContent = ETIQUETAS_ROL[usuario.rol] || usuario.rol;
    sello.classList.add(CLASES_ROL[usuario.rol] || 'sello--de-baja');

    nodo.querySelector('[data-accion="editar"]').addEventListener('click', () => abrirModalEditar(usuario));

    const botonEliminar = nodo.querySelector('[data-accion="eliminar"]');
    if (usuario.id === USUARIO_ACTUAL_ID) {
        // Protección extra en la interfaz: el backend también lo rechaza,
        // pero así ni siquiera se puede intentar.
        botonEliminar.disabled = true;
        botonEliminar.textContent = 'Esta es tu cuenta';
    } else {
        botonEliminar.addEventListener('click', () => eliminarUsuario(usuario.id, usuario.nombre_usuario));
    }

    return nodo;
}

async function eliminarUsuario(id, nombreUsuario) {
    const confirmado = confirm(`¿Eliminar la cuenta ${nombreUsuario}? Esta acción no se puede deshacer.`);
    if (!confirmado) return;

    try {
        const respuesta = await fetch(`/api/usuarios/${id}`, { method: 'DELETE' });
        const resultado = await respuesta.json();
        if (!respuesta.ok) throw new Error(resultado.error || 'No se pudo eliminar la cuenta');
        cargarUsuarios();
    } catch (error) {
        mostrarError(error.message);
    }
}

// ---------- Modal: añadir cuenta nueva ----------

function abrirModal() {
    formNuevaCuenta.reset();
    modalError.classList.add('oculto');
    modal.classList.remove('oculto');
    document.getElementById('nombre_completo').focus();
}

function cerrarModal() {
    modal.classList.add('oculto');
}

document.getElementById('btn-abrir-modal').addEventListener('click', abrirModal);
document.getElementById('btn-cancelar-modal').addEventListener('click', cerrarModal);

modal.addEventListener('click', (evento) => {
    if (evento.target === modal) cerrarModal();
});

formNuevaCuenta.addEventListener('submit', async (evento) => {
    evento.preventDefault();
    modalError.classList.add('oculto');

    const datos = {
        nombre_completo: document.getElementById('nombre_completo').value.trim(),
        nombre_usuario: document.getElementById('nombre_usuario').value.trim(),
        correo: document.getElementById('correo').value.trim(),
        contrasena: document.getElementById('contrasena').value,
        rol: document.getElementById('rol').value,
    };

    try {
        const respuesta = await fetch('/api/usuarios', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(datos),
        });
        const resultado = await respuesta.json();

        if (!respuesta.ok) throw new Error(resultado.error || 'No se pudo crear la cuenta');

        cerrarModal();
        cargarUsuarios();
    } catch (error) {
        modalError.textContent = error.message;
        modalError.classList.remove('oculto');
    }
});

// ---------- Modal: editar cuenta existente ----------

function abrirModalEditar(usuario) {
    modalEditarError.classList.add('oculto');
    document.getElementById('editar_id').value = usuario.id;
    document.getElementById('editar_nombre_completo').value = usuario.nombre_completo;
    document.getElementById('editar_correo').value = usuario.correo || '';
    document.getElementById('editar_rol').value = usuario.rol;
    modalEditar.classList.remove('oculto');
    document.getElementById('editar_nombre_completo').focus();
}

function cerrarModalEditar() {
    modalEditar.classList.add('oculto');
}

document.getElementById('btn-cancelar-editar').addEventListener('click', cerrarModalEditar);

modalEditar.addEventListener('click', (evento) => {
    if (evento.target === modalEditar) cerrarModalEditar();
});

formEditarCuenta.addEventListener('submit', async (evento) => {
    evento.preventDefault();
    modalEditarError.classList.add('oculto');

    const id = document.getElementById('editar_id').value;
    const datos = {
        nombre_completo: document.getElementById('editar_nombre_completo').value.trim(),
        correo: document.getElementById('editar_correo').value.trim(),
        rol: document.getElementById('editar_rol').value,
    };

    try {
        const respuesta = await fetch(`/api/usuarios/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(datos),
        });
        const resultado = await respuesta.json();

        if (!respuesta.ok) throw new Error(resultado.error || 'No se pudo actualizar la cuenta');

        cerrarModalEditar();
        cargarUsuarios();
    } catch (error) {
        modalEditarError.textContent = error.message;
        modalEditarError.classList.remove('oculto');
    }
});

// ---------- Arranque ----------
cargarUsuarios();
