/* ============================================================
   detalle.js
   Lógica de la ficha individual de un equipo (computador_detalle.html):
   - Carga los datos del equipo con fetch GET usando COMPUTADOR_ID
   - Alterna entre modo "solo lectura" y modo "edición"
   - Guarda los cambios con fetch PUT
   - Elimina el equipo con fetch DELETE
   ============================================================ */

const tituloFicha = document.getElementById('titulo-ficha');
const mensajeError = document.getElementById('mensaje-error');
const formFicha = document.getElementById('form-ficha');

const sello = document.getElementById('sello-estado');
const contenedorSelectEstado = document.getElementById('contenedor-estado-select');
const campoEstado = document.getElementById('estado');

const campoNumero = document.getElementById('numero_computador');
const campoMarca = document.getElementById('marca');
const campoSerial = document.getElementById('serial');
const campoFicha = document.getElementById('ficha_mantenimiento');
const fechaRegistro = document.getElementById('fecha-registro');

const btnEditar = document.getElementById('btn-editar');
const btnGuardar = document.getElementById('btn-guardar');
const btnCancelar = document.getElementById('btn-cancelar');
const btnEliminar = document.getElementById('btn-eliminar');

const camposEditables = [campoNumero, campoMarca, campoSerial, campoFicha];

let datosActuales = null;

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

// ---------- Cargar los datos del equipo ----------

async function cargarComputador() {
    try {
        const respuesta = await fetch(`/api/computadores/${COMPUTADOR_ID}`);
        if (!respuesta.ok) throw new Error('No se encontró el equipo solicitado');

        datosActuales = await respuesta.json();
        rellenarFormulario(datosActuales);
    } catch (error) {
        tituloFicha.textContent = 'Equipo no encontrado';
        mostrarError(error.message);
    }
}

function rellenarFormulario(computador) {
    tituloFicha.textContent = computador.numero_computador;

    campoNumero.value = computador.numero_computador;
    campoMarca.value = computador.marca;
    campoSerial.value = computador.serial;
    campoFicha.value = computador.ficha_mantenimiento || '';
    campoEstado.value = computador.estado;

    sello.textContent = computador.estado;
    sello.className = 'sello ' + claseParaEstado(computador.estado);

    fechaRegistro.textContent = computador.fecha_registro
        ? `Registrado el ${computador.fecha_registro}`
        : '';
}

// ---------- Alternar entre modo vista y modo edición ----------

function activarModoEdicion() {
    camposEditables.forEach((campo) => (campo.disabled = false));
    campoNumero.focus();

    sello.classList.add('oculto');
    contenedorSelectEstado.classList.remove('oculto');

    btnEditar.classList.add('oculto');
    btnGuardar.classList.remove('oculto');
    btnCancelar.classList.remove('oculto');
}

function activarModoLectura() {
    camposEditables.forEach((campo) => (campo.disabled = true));

    sello.classList.remove('oculto');
    contenedorSelectEstado.classList.add('oculto');

    btnEditar.classList.remove('oculto');
    btnGuardar.classList.add('oculto');
    btnCancelar.classList.add('oculto');
}

// Editar la ficha (incluido el estado) lo pueden hacer 'admin' y 'editor'.
// Eliminar el equipo solo lo puede hacer 'admin' (btnEliminar ni siquiera
// existe en el HTML para 'editor', ver computador_detalle.html).
if (ROL_USUARIO === 'admin' || ROL_USUARIO === 'editor') {
    btnEditar.addEventListener('click', activarModoEdicion);

    btnCancelar.addEventListener('click', () => {
        rellenarFormulario(datosActuales); // descarta cambios no guardados
        activarModoLectura();
    });

    // ---------- Guardar cambios ----------

    formFicha.addEventListener('submit', async (evento) => {
        evento.preventDefault();

        const datos = {
            numero_computador: campoNumero.value.trim(),
            marca: campoMarca.value.trim(),
            serial: campoSerial.value.trim(),
            estado: campoEstado.value,
            ficha_mantenimiento: campoFicha.value.trim(),
        };

        try {
            const respuesta = await fetch(`/api/computadores/${COMPUTADOR_ID}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(datos),
            });
            const resultado = await respuesta.json();

            if (!respuesta.ok) throw new Error(resultado.error || 'No se pudo guardar la ficha');

            await cargarComputador();
            activarModoLectura();
        } catch (error) {
            mostrarError(error.message);
        }
    });

    // ---------- Eliminar equipo (solo 'admin') ----------

    if (btnEliminar) {
        btnEliminar.addEventListener('click', async () => {
            const confirmado = confirm('¿Eliminar este equipo? Esta acción no se puede deshacer.');
            if (!confirmado) return;

            try {
                const respuesta = await fetch(`/api/computadores/${COMPUTADOR_ID}`, { method: 'DELETE' });
                if (!respuesta.ok) throw new Error('No se pudo eliminar el equipo');

                window.location.href = '/';
            } catch (error) {
                mostrarError(error.message);
            }
        });
    }
}

// ---------- Arranque ----------
cargarComputador();
