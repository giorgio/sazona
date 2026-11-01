"""sazón.: recetas sanas y baratas de todo el mundo, con su precio por porción.

Hermana de canastas. Páginas:
  - Explorar recetas: filtros (cocina, personas, precio, tiempo, tipo) y tarjetas con foto y precio.
  - Mi semana: las recetas elegidas, una sola lista de compras en paquetes enteros,
    ideas para lo que sobra y enlace a canastas. para comparar tiendas.

Ejecutar en local:  streamlit run app.py
Claves en .streamlit/secrets.toml o en los Secrets de Streamlit Cloud: GEMINI_API_KEY y PEXELS_API_KEY.
"""

import os
import time

import streamlit as st

import diseno as d
import fotos
import nucleo as n

ICONO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icono.png")
st.set_page_config(page_title="sazón.", page_icon=ICONO if os.path.exists(ICONO) else "🍲", layout="wide")

ESPERA_ENTRE_CONSULTAS = 6
INICIALES = {"pagina": "explorar", "recetas": [], "menu": [], "ideas_sobra": [],
             "f_cocinas": ["Ecuatoriana", "Italiana", "China", "Mexicana"], "f_personas": 2,
             "f_max": 1.5, "f_tiempo": 45, "f_tipos": []}
for _k, _v in INICIALES.items():
    st.session_state.setdefault(_k, _v)


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def ir(pagina):
    st.session_state["pagina"] = pagina


def secreto(nombre):
    try:
        return st.secrets.get(nombre)
    except Exception:  # noqa: BLE001
        return None


def obtener_cliente():
    clave = secreto("GEMINI_API_KEY")
    if not clave:
        st.error("Falta la clave de la IA (GEMINI_API_KEY) en los Secrets de la app.")
        st.stop()
    from google import genai

    return genai.Client(api_key=clave)


def esperar_turno():
    falta = ESPERA_ENTRE_CONSULTAS - (time.time() - st.session_state.get("ultima_consulta", 0))
    if falta > 0:
        time.sleep(falta)
    st.session_state["ultima_consulta"] = time.time()


@st.cache_data(ttl=7 * 86400, show_spinner=False)
def foto(consulta: str):
    return fotos.buscar_foto(consulta, secreto("PEXELS_API_KEY"))


def en_menu(r) -> bool:
    return any(m.nombre == r.nombre for m in st.session_state["menu"])


def alternar_menu(r):
    if en_menu(r):
        st.session_state["menu"] = [m for m in st.session_state["menu"] if m.nombre != r.nombre]
    else:
        st.session_state["menu"] = st.session_state["menu"] + [r]


def alto(filas):
    return 36 + 35 * max(len(filas), 1)


# ---------------------------------------------------------------------------
# Tarjeta y detalle de receta
# ---------------------------------------------------------------------------

@st.dialog("Receta", width="large")
def ver_receta(r):
    f = foto(r.busqueda_foto)
    c1, c2 = st.columns([1, 1.2], gap="large")
    with c1:
        if f:
            st.image(f["url"], width="stretch")
            d.credito_foto(f)
        else:
            d.foto_vacia()
    with c2:
        d.info_receta(r, n.costo_porcion(r), n.costo_receta(r))
        st.caption(f"Dificultad: {r.dificultad}")
        st.button("Quitar de mi semana" if en_menu(r) else "Agregar a mi semana",
                  icon=":material/remove:" if en_menu(r) else ":material/add:",
                  on_click=alternar_menu, args=(r,), type="secondary" if en_menu(r) else "primary", width="stretch")
    st.subheader("Ingredientes")
    filas = n.tabla_ingredientes(r)
    st.dataframe(filas, hide_index=True, width="stretch", height=alto(filas),
                 column_config={"Costo en la receta": st.column_config.NumberColumn(format="$%.2f")})
    st.caption("“Costo en la receta” es solo la parte que usas del paquete. Precios estimados.")
    st.subheader("Preparación")
    for i, p in enumerate(r.pasos, 1):
        st.markdown(f"{i}. {p}")
    st.info("💚 " + r.por_que_es_saludable)


def tarjeta(r, clave: str):
    with st.container(border=True, key=f"rc_{clave}"):
        f = foto(r.busqueda_foto)
        if f:
            st.image(f["url"], width="stretch")
            d.credito_foto(f)
        else:
            d.foto_vacia()
        d.info_receta(r, n.costo_porcion(r), n.costo_receta(r))
        if st.button("Ver receta", key=f"ver_{clave}", icon=":material/menu_book:", width="stretch"):
            ver_receta(r)
        with st.container(key=f"en_menu_{clave}" if en_menu(r) else f"fuera_{clave}"):
            st.button("En mi semana" if en_menu(r) else "A mi semana",
                      icon=":material/check:" if en_menu(r) else ":material/add:",
                      key=f"menu_{clave}", on_click=alternar_menu, args=(r,), width="stretch")


def cuadricula(recetas, prefijo: str):
    for fila in range(0, len(recetas), 3):
        cols = st.columns(3, gap="medium")
        for j, r in enumerate(recetas[fila:fila + 3]):
            with cols[j]:
                tarjeta(r, f"{prefijo}_{fila + j}")


# ---------------------------------------------------------------------------
# Página: explorar recetas
# ---------------------------------------------------------------------------

def buscar(mas: bool = False):
    s = st.session_state
    val = n.validar_busqueda(s["f_cocinas"], s["f_personas"], s["f_max"], s["f_tiempo"])
    for e in val.errores:
        st.error(e)
    if not val.ok:
        return
    esperar_turno()
    cliente = obtener_cliente()
    with st.spinner("Buscando recetas ricas y baratas… unos 20 segundos"):
        try:
            nuevas, _ = n.buscar_recetas(
                cliente, s["f_cocinas"], s["f_personas"], s["f_max"], s["f_tiempo"], s["f_tipos"],
                excluir=[r.nombre for r in s["recetas"]] if mas else [])
        except n.ErrorIA as e:
            st.error(str(e))
            return
    s["recetas"] = (s["recetas"] + nuevas) if mas else nuevas


def pagina_explorar():
    d.titulo("Cocina rico, gasta poco", "¿Qué cocinamos?",
             "Recetas de todo el mundo con ingredientes de aquí, cada una con su precio por porción.")
    with st.container(border=True, key="tarjeta"):
        with st.form("filtros", border=False):
            st.multiselect("Cocinas", n.COCINAS, key="f_cocinas", placeholder="Elige una o varias")
            c1, c2, c3 = st.columns(3, gap="medium")
            c1.number_input("Personas", min_value=1, max_value=12, key="f_personas")
            c2.select_slider("Máximo por porción", options=[0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0], key="f_max",
                             format_func=lambda x: f"${x:.2f}")
            c3.select_slider("Tiempo máximo", options=[15, 20, 30, 45, 60, 90], key="f_tiempo",
                             format_func=lambda x: f"{x} min")
            st.multiselect("Tipo (opcional)", n.TIPOS, key="f_tipos", placeholder="Cualquiera")
            buscar_ya = st.form_submit_button("Buscar recetas", icon=":material/search:", type="primary",
                                              width="stretch")
    if buscar_ya:
        buscar()
    recetas = st.session_state["recetas"]
    if recetas:
        st.write("")
        st.markdown(f"**{len(recetas)} recetas**, de la más barata a la más cara · precios estimados")
        cuadricula(recetas, "ex")
        st.write("")
        if st.button("Ver más recetas", icon=":material/refresh:", width="stretch"):
            buscar(mas=True)
            st.rerun()


# ---------------------------------------------------------------------------
# Página: mi semana
# ---------------------------------------------------------------------------

def pagina_semana():
    menu = st.session_state["menu"]
    d.titulo("Tu plan de la semana", "Mi semana.",
             "Las recetas que elegiste, en una sola lista de compras.")
    if not menu:
        with st.container(border=True, key="tarjeta"):
            st.markdown("Todavía no agregas recetas. Explora y pulsa **A mi semana** en las que te gusten.")
            st.button("Explorar recetas", icon=":material/restaurant_menu:", on_click=ir, args=("explorar",),
                      type="primary")
        return

    lista = n.lista_de_compras(menu)
    porciones = sum(r.porciones for r in menu)
    d.resumen([
        ("Recetas", str(len(menu)), False),
        ("Compras de la semana", f"${lista['total']:.2f}", True),
        ("Lo que cocinas", f"${n.costo_menu(menu):.2f}", False),
        ("Promedio por porción", f"${n.costo_menu(menu) / max(porciones, 1):.2f}", False),
    ])
    st.caption("“Compras” es lo que pagas en la tienda (paquetes enteros). “Lo que cocinas” es solo lo que usan "
               "las recetas: la diferencia es lo que te sobra para otras comidas.")

    with st.container(border=True, key="tarjeta"):
        st.subheader("Tus recetas")
        for i, r in enumerate(menu):
            c1, c2, c3 = st.columns([4, 1.4, 1], vertical_alignment="center")
            c1.markdown(f"**{r.nombre}** · {r.cocina} · {r.tiempo_minutos} min")
            c2.markdown(f"**${n.costo_porcion(r):.2f}** por porción")
            if c3.button("Quitar", key=f"quitar_{i}", icon=":material/close:", width="stretch"):
                alternar_menu(r)
                st.rerun()

        st.subheader("Lista de compras")
        st.dataframe(lista["comprar"], hide_index=True, width="stretch", height=alto(lista["comprar"]),
                     column_config={"Precio": st.column_config.NumberColumn(format="$%.2f"),
                                    "Para": st.column_config.TextColumn(width="medium")})
        if lista["despensa"]:
            st.caption("Revisa si ya tienes en casa: " + ", ".join(f["Ingrediente"] for f in lista["despensa"]))
        b1, b2 = st.columns(2, gap="medium")
        b1.download_button("Descargar lista", n.texto_lista(menu, lista).encode("utf-8"), "lista_sazon.txt",
                           "text/plain", icon=":material/download:", width="stretch")
        b2.link_button("Ver dónde comprar más barato en canastas.", n.enlace_canastas(lista),
                       icon=":material/shopping_basket:", width="stretch")

    seccion_sobrantes(lista)


def seccion_sobrantes(lista):
    st.write("")
    with st.container(border=True, key="tarjeta_sobra"):
        st.subheader("♻️ Lo que te sobra")
        if not lista["sobrantes"]:
            st.markdown("¡Bien! Con estas recetas casi no te sobra nada.")
            return
        for s in lista["sobrantes"]:
            st.markdown(f"- **{s['nombre']}**: te queda cerca del **{s['sobra']:.0%}** de {s['presentacion']}")
        if st.button("Darme ideas para aprovecharlo", icon=":material/lightbulb:", type="primary"):
            s_ = st.session_state
            esperar_turno()
            cliente = obtener_cliente()
            with st.spinner("Buscando recetas con lo que te sobra…"):
                try:
                    s_["ideas_sobra"], _ = n.buscar_recetas(
                        cliente, s_["f_cocinas"] or n.COCINAS[:4], s_["f_personas"], max(s_["f_max"], 1.5),
                        s_["f_tiempo"], s_["f_tipos"], excluir=[r.nombre for r in s_["menu"]],
                        sobrantes=[x["nombre"] for x in lista["sobrantes"]])
                except n.ErrorIA as e:
                    st.error(str(e))
    if st.session_state["ideas_sobra"]:
        st.write("")
        st.markdown("**Ideas para aprovechar lo que sobra**")
        cuadricula(st.session_state["ideas_sobra"], "sob")


# ---------------------------------------------------------------------------
# Página principal
# ---------------------------------------------------------------------------

d.aplicar_estilos()
d.cabecera()
pagina = st.session_state["pagina"]
col_menu, col_pagina = st.columns([1, 3], gap="large")
with col_menu:
    d.menu(pagina, ir, len(st.session_state["menu"]))
with col_pagina:
    {"explorar": pagina_explorar, "semana": pagina_semana}.get(pagina, pagina_explorar)()

st.divider()
st.caption("sazón. · hermana de canastas. · IA: Google Gemini · Fotos: [Wikimedia Commons](https://commons.wikimedia.org) · "
           "Precios y valores nutricionales aproximados.")
