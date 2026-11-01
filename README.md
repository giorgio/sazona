# sazón.

**Rico, sano y barato.** Recetas saludables de todo el mundo (ecuatoriana, italiana, china, mexicana, peruana…) adaptadas a ingredientes que se consiguen en Ecuador, cada una con su **precio por porción**.

App hermana de **canastas.**

## Qué hace

1. **Explorar recetas**: eliges cocinas, cuántas personas, cuánto quieres gastar por porción, el tiempo máximo y, si quieres, un tipo (alta en proteína, vegetariana, para niños…). La app trae recetas ordenadas de la más barata a la más cara, con foto, calorías y proteína.
2. **Mi semana**: agregas las recetas que te gusten y la app arma **una sola lista de compras** con paquetes enteros (lo que de verdad pagas en la tienda).
3. **Lo que te sobra**: como compras paquetes completos, siempre sobra algo. La app te dice qué y cuánto, y te da recetas para aprovecharlo.
4. **Conectar con canastas**: un botón abre canastas con tu lista para ver dónde comprar más barato.

## Cómo se calculan los precios

La IA (Google Gemini) propone las recetas y estima el precio de cada presentación en Ecuador (por ejemplo, "funda de fideo 500 g: $1.20") y qué parte se usa. **Las sumas las hace la app**, no la IA:

- Costo de un ingrediente = precio del paquete × parte que usa la receta.
- Lista de compras = paquetes enteros (si dos recetas usan media funda de fideo, compras una).
- Sobrante = paquetes comprados − lo que usan las recetas.

Los precios son estimados: confírmalos en la tienda.

## Fotos

Fotos libres de **Wikimedia Commons** (sin clave), con crédito al autor y la licencia. Si se agrega `PEXELS_API_KEY` en los Secrets, se usa Pexels primero. Si no hay foto, aparece la ilustración de la marca.

## Ejecutar en tu computadora

```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # y pon tu clave de Gemini
streamlit run app.py
```

Pruebas (sin internet ni cuota): `python tests/test_nucleo.py`

## Publicar en Streamlit Community Cloud

1. Sube esta carpeta a un repositorio nuevo de GitHub (sin `secrets.toml`).
2. En share.streamlit.io → **Create app** → elige el repositorio, rama `main`, archivo `app.py`.
3. En **Advanced settings → Secrets** pega:
   ```toml
   GEMINI_API_KEY = "tu-clave"
   ```
4. Deploy.

## Archivos

| Archivo | Qué contiene |
|---|---|
| `app.py` | Pantallas y navegación (Streamlit) |
| `nucleo.py` | Lógica: modelos de datos, llamada a Gemini, costos, lista de compras, sobrantes |
| `fotos.py` | Búsqueda de fotos (Wikimedia Commons / Pexels) |
| `diseno.py` | Colores, tipografía, cabecera, menú y tarjetas |
| `tests/test_nucleo.py` | Pruebas de la lógica |

Autor: Jorge Recabarren
