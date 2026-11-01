# AGENTS.md — guía para asistentes de código

## Reglas
- Español neutro en la interfaz (tú, no vos).
- Nunca escribir claves en el código. Se leen de `st.secrets` (`GEMINI_API_KEY`, `PEXELS_API_KEY` opcional). `.streamlit/secrets.toml` está en `.gitignore`.
- La IA no suma dinero: devuelve precio por presentación y `fraccion_usada`; todos los totales salen de `nucleo.py`.
- Mantener el diseño compartido con canastas (DM Sans, cabecera con isotipo, ceja en mayúsculas + título grande, tarjeta blanca, menú a la izquierda). Paleta terracota en `diseno.py`.

## Estructura
- `nucleo.py`: sin Streamlit, se prueba solo. `buscar_recetas()` devuelve `(recetas, descartadas)` y lanza `ErrorIA` con un mensaje listo para mostrar.
- `app.py`: estado en `st.session_state` (`pagina`, `recetas`, `menu`, `ideas_sobra`, filtros `f_*`).
- `fotos.py`: `buscar_foto(consulta, clave_pexels)` → dict con url, autor, página, licencia y fuente, o `None`.
- Modelo: `gemini-3.8-flash`, respaldo `gemini-3.5-flash-lite` si hay 404/429.

## Antes de entregar cambios
```bash
python tests/test_nucleo.py
```
Debe imprimir `TODAS LAS PRUEBAS DE SAZÓN OK`.

## Pendiente
- canastas aún no lee `?productos=` en la URL; el botón ya envía la lista.
