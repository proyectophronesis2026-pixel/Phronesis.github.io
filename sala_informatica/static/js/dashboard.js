/* ============================================================
   dashboard.js
   Lógica de la pantalla principal (index.html):
   - Pide la lista de computadores a la API (fetch GET)
   - Dibuja una tarjeta por cada uno
   - Controla el formulario modal para añadir un equipo (fetch POST)
   - Controla el botón "Eliminar" de cada tarjeta (fetch DELETE)
   ============================================================ */

const grid = document.getElementById('grid-equipos');
const contador = document.getElementById('contador-equipos');
const mensajeVacio = document.getElementById('mensaje-vacio');
const mensajeError = document.getElementById('mensaje-error');
const plantillaTarjeta = document.getElementById('plantilla-tarjeta');

const modal = document.getElementById('modal-nuevo-equipo');
const formNuevoEquipo = document.getElementById('form-nuevo-equipo');
const modalError = document.getElementById('modal-error');

// Traduce el texto del estado a la clase CSS del "sello"
function claseParaEstado(estado) {
    const mapa = {
        'Activo': 'sello--activo',
        'En mantenimiento': 'sello--en-mantenimiento',
        'Dañado': 'sello--danado',
        'De baja': 'sello--de-baja',
    };
    return mapa[estado] || 'sello--activo';
}

function mostrarError(texto) {
    mensajeError.textContent = texto;
    mensajeError.classList.remove('oculto');
}

function ocultarError() {
    mensajeError.classList.add('oculto');
}

// ---------- Cargar y dibujar la lista ----------

async function cargarComputadores() {
    ocultarError();
    try {
        const respuesta = await fetch('/api/computadores');
        if (!respuesta.ok) throw new Error('No se pudo obtener la lista de equipos');

        const computadores = await respuesta.json();
        dibujarLista(computadores);
    } catch (error) {
        mostrarError('Error al cargar los equipos: ' + error.message);
    }
}

function dibujarLista(computadores) {
    grid.innerHTML = '';

    if (computadores.length === 0) {
        mensajeVacio.classList.remove('oculto');
    } else {
        mensajeVacio.classList.add('oculto');
    }

    contador.textContent = computadores.length === 1
        ? '1 equipo registrado'
        : `${computadores.length} equipos registrados`;

    computadores.forEach((computador) => grid.appendChild(crearTarjeta(computador)));
}

function crearTarjeta(computador) {
    const nodo = plantillaTarjeta.content.cloneNode(true);

    nodo.querySelector('.ficha-equipo__numero').textContent = computador.numero_computador;
    nodo.querySelector('.ficha-equipo__marca').textContent = computador.marca;
    nodo.querySelector('.ficha-equipo__serial').textContent = 'S/N ' + computador.serial;

    const sello = nodo.querySelector('.sello');
    sello.textContent = computador.estado;
    sello.classList.add(claseParaEstado(computador.estado));

    const enlaceVer = nodo.querySelector('[data-accion="ver"]');
    enlaceVer.href = `/computador/${computador.id}`;

    const botonEliminar = nodo.querySelector('[data-accion="eliminar"]');
    if (botonEliminar) {
        botonEliminar.addEventListener('click', () => eliminarComputador(computador.id, computador.numero_computador));
    }

    return nodo;
}

async function eliminarComputador(id, numeroComputador) {
    const confirmado = confirm(`¿Eliminar el equipo ${numeroComputador}? Esta acción no se puede deshacer.`);
    if (!confirmado) return;

    try {
        const respuesta = await fetch(`/api/computadores/${id}`, { method: 'DELETE' });
        if (!respuesta.ok) throw new Error('No se pudo eliminar el equipo');
        cargarComputadores();
    } catch (error) {
        mostrarError(error.message);
    }
}

// ---------- Modal: añadir equipo nuevo ----------

function abrirModal() {
    formNuevoEquipo.reset();
    modalError.classList.add('oculto');
    modal.classList.remove('oculto');
    document.getElementById('numero_computador').focus();
}

function cerrarModal() {
    modal.classList.add('oculto');
}

if (ROL_USUARIO === 'admin') {
    document.getElementById('btn-abrir-modal').addEventListener('click', abrirModal);
    document.getElementById('btn-cancelar-modal').addEventListener('click', cerrarModal);

    // Cerrar el modal si se hace clic fuera del panel
    modal.addEventListener('click', (evento) => {
        if (evento.target === modal) cerrarModal();
    });

    formNuevoEquipo.addEventListener('submit', async (evento) => {
        evento.preventDefault();
        modalError.classList.add('oculto');

        const datos = {
            numero_computador: document.getElementById('numero_computador').value.trim(),
            marca: document.getElementById('marca').value.trim(),
            serial: document.getElementById('serial').value.trim(),
            estado: document.getElementById('estado').value,
            ficha_mantenimiento: document.getElementById('ficha_mantenimiento').value.trim(),
        };

        try {
            const respuesta = await fetch('/api/computadores', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(datos),
            });
            const resultado = await respuesta.json();

            if (!respuesta.ok) throw new Error(resultado.error || 'No se pudo guardar el equipo');

            cerrarModal();
            cargarComputadores();
        } catch (error) {
            modalError.textContent = error.message;
            modalError.classList.remove('oculto');
        }
    });
}

// ---------- Arranque ----------
cargarComputadores();
