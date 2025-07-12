import streamlit as st
import pandas as pd

# --- PARÁMETROS --- #
params = {
    'demanda_base': 2000,
    'p': 25, 'd': 0.10,
    'c_p': 5, 'c_n': 520, 'c_c': 400, 'c_d': 500,
    'c_h': 20, 'c_inv': 4, 'c_f': 14,
    'C_A': 400, 'C_E': 200,
    'v': 6, 'v_ex': 5,
    'h_reg': 40, 'h_ext': 10,
    'N_min': 5, 'N_max': 8,
    'k_P': 550, 'k_A': 400, 'k_E': 200,
    'K_P': 3, 'K_A': 4, 'K_E': 5
}
T = 12

estado_inicial = {
    "inventario": 200,
    "n": 5,
    "kP": 0, "kA": 0, "kE": 0,
    "acum_mkt": 0,
    "acum_ops": 0,
    "historico": []
}

if "inicio" not in st.session_state:
    st.session_state.inicio = False
    st.session_state.periodo = 1
    st.session_state.estado = estado_inicial.copy()

# --- REGISTRO INICIAL --- #
if not st.session_state.inicio:
    st.title("Simulación S&OP – Registro")
    st.session_state.correo = st.text_input("Correo UTEC")
    st.session_state.turno = st.selectbox("Turno", ["Turno 1 (4:00pm)", "Turno 2 (6:00pm)"])
    st.session_state.duo = st.selectbox("Número de dúo", list(range(1, 8)))
    rol = st.selectbox("Rol asignado", ["Marketing", "Operaciones"])
    if st.button("Ingresar"):
        st.session_state.inicio = True
        st.session_state.rol = rol
        st.rerun()
    st.stop()

# --- PARÁMETROS DE SESIÓN --- #
rol = st.session_state.get('rol', None)
if rol is None:
    st.stop()

st.sidebar.title("📊 Avance")
st.sidebar.markdown(f"Semana **{st.session_state.periodo} de {T}**")

estado = st.session_state.estado
periodo = st.session_state.periodo
inv = estado['inventario']
n_ant = estado['n']
kP, kA, kE = estado['kP'], estado['kA'], estado['kE']

P = A = E = delta_n = h_reg = h_ext = 0
op_decision = (0, 0, 0)
mkt_decision = (False, False, False)



if rol == "Marketing":
    st.title(f"Semana {periodo} – Rol Marketing")
    st.subheader("🎯 Tus decisiones de Marketing")

    maxP = estado["kP"] < params["K_P"]
    maxA = estado["kA"] < params["K_A"]
    maxE = estado["kE"] < params["K_E"]

    if not maxP:
        st.warning("⚠️ Ya se usaron todas las promociones permitidas.")
    if not maxA:
        st.warning("⚠️ Ya se usaron todos los anuncios permitidos.")
    if not maxE:
        st.warning("⚠️ Ya se usaron todas las exhibiciones permitidas.")

    P = st.checkbox("¿Promoción?", disabled=not maxP)
    A = st.checkbox("¿Anuncio?", disabled=not maxA)
    E = st.checkbox("¿Exhibición?", disabled=not maxE)
    mkt_decision = (P, A, E)

    # Cálculos actualizados
    demanda = params['demanda_base'] + params['k_P'] * P + params['k_A'] * A + params['k_E'] * E
    ventas_estimadas = min(demanda, estado["inventario"])  # No se suma producción, porque no la conoce
    ingresos = params['p'] * ventas_estimadas
    descuentos = params['d'] * params['p'] * (ventas_estimadas if P else 0)
    costos_mkt = descuentos + params['C_A'] * A + params['C_E'] * E
    utilidad = ingresos - costos_mkt

    st.subheader("📈 Resultados estimados")
    st.metric("Demanda inducida", f"{demanda}")
    st.metric("Ventas estimadas", f"{ventas_estimadas}")
    st.metric("Utilidad semanal MKT", f"${round(utilidad, 2)}")
    st.metric("Utilidad acumulada", f"${round(estado['acum_mkt'] + utilidad, 2)}")

    # Gráfica detallada
    if estado['historico']:
        df_hist = pd.DataFrame(estado['historico'])
        df_hist['ingresos_mkt'] = df_hist['Ventas'] * params['p']
        df_hist['descuentos'] = df_hist.apply(lambda row: row['W'] * params['p'] * params['d'], axis=1)
        df_hist['costos_mkt'] = df_hist['descuentos'] + df_hist['Anuncio'] * params['C_A'] + df_hist['Exhibición'] * params['C_E']
        df_hist['U_MKT'] = df_hist['ingresos_mkt'] - df_hist['costos_mkt']
        df_acum = df_hist[['ingresos_mkt', 'costos_mkt', 'U_MKT']].cumsum()
        st.line_chart(df_acum.rename(columns={
            'ingresos_mkt': 'Ingresos acumulados',
            'costos_mkt': 'Costos acumulados',
            'U_MKT': 'Utilidad acumulada'
        }))


    st.subheader("📩 Decisiones de Operaciones (ingrésalas aquí)")
    delta_n = st.slider("Cambio de trabajadores", -3, 3, 0, key='mkt_delta')
    h_reg = st.slider("Horas regulares", 0, params['h_reg'], 40, key='mkt_reg')
    h_ext = st.slider("Horas extra", 0, params['h_ext'], 0, key='mkt_ext')
    op_decision = (delta_n, h_reg, h_ext)



# --- VISTA OPERACIONES --- #


elif rol == "Operaciones":
    st.title(f"Semana {periodo} – Rol Operaciones")
    st.subheader("🔧 Tus decisiones de Operaciones")

    n_ant = estado['n']
    min_delta = max(params['N_min'] - n_ant, -3)
    max_delta = min(params['N_max'] - n_ant, 3)

    delta_n = st.slider(f"Cambio de trabajadores (actual: {n_ant})", min_delta, max_delta, 0, key='ops_delta')
    h_reg = st.slider("Horas regulares", 0, params['h_reg'], 40, key='ops_reg')
    h_ext = st.slider("Horas extra", 0, params['h_ext'], 0, key='ops_ext')
    op_decision = (delta_n, h_reg, h_ext)

    n = n_ant + delta_n
    produccion = n * (h_reg * params['v'] + h_ext * params['v_ex'])

    demanda = params['demanda_base']  # Producción no ve campañas aún
    inventario_final = max(0, estado['inventario'] + produccion - demanda)
    faltantes = max(0, demanda - (estado['inventario'] + produccion))

    costo_produccion = params['c_p'] * produccion
    costo_nomina = params['c_n'] * n
    costo_contratacion = params['c_c'] * max(0, delta_n)
    costo_despido = params['c_d'] * max(0, -delta_n)
    costo_horas_extra = params['c_h'] * h_ext * n
    costo_inventario = params['c_inv'] * inventario_final
    costo_faltantes = params['c_f'] * faltantes

    costo_total = -(
        costo_produccion + costo_nomina + costo_contratacion +
        costo_despido + costo_horas_extra + costo_inventario + costo_faltantes
    )

    st.subheader("📊 Resultados y estado")
    st.metric("Trabajadores activos", n)
    st.metric("Producción total", f"{produccion} unidades")
    st.metric("Inventario final estimado", f"{inventario_final} unidades")
    st.metric("Faltantes esperados", f"{faltantes} unidades")
    st.metric("Costo semanal OPS", f"${round(costo_total, 2)}")
    st.metric("Costo acumulado", f"${round(estado['acum_ops'] + costo_total, 2)}")

    # Gráficas
    if estado['historico']:
        df_hist = pd.DataFrame(estado['historico'])
        df_acum = df_hist[['C_OPS', 'Inventario']].copy()
        df_acum['Costo acumulado'] = df_acum['C_OPS'].cumsum()
        df_acum['Inventario acumulado'] = df_acum['Inventario'].cumsum()

        st.line_chart(df_acum[['Costo acumulado', 'Inventario acumulado']])


    st.subheader("📩 Decisiones de Marketing (ingrésalas aquí)")
    P = st.checkbox("¿Promoción?")
    A = st.checkbox("¿Anuncio?")
    E = st.checkbox("¿Exhibición?")
    mkt_decision = (P, A, E)


# --- CONFIRMAR Y AVANZAR --- #
if st.button("✅ Confirmar y avanzar"):
    P, A, E = mkt_decision
    delta_n, h_reg, h_ext = op_decision
    n = n_ant + delta_n
    produccion = n * (h_reg * params['v'] + h_ext * params['v_ex'])
    demanda = params['demanda_base'] + params['k_P'] * P + params['k_A'] * A + params['k_E'] * E
    ventas = min(demanda, inv + produccion)
    nuevo_inv = max(0, inv + produccion - ventas)
    faltantes = max(0, demanda - ventas)
    h_tot = h_ext * n
    W = ventas if P else 0

    r_mkt = params['p'] * ventas - params['d'] * params['p'] * W - params['C_A'] * A - params['C_E'] * E
    r_ops = -(
        params['c_p'] * produccion + params['c_n'] * n +
        params['c_c'] * max(0, delta_n) + params['c_d'] * max(0, -delta_n) +
        params['c_h'] * h_tot + params['c_inv'] * nuevo_inv + params['c_f'] * faltantes
    )

    estado['inventario'] = nuevo_inv
    estado['n'] = n
    estado['kP'] += P
    estado['kA'] += A
    estado['kE'] += E
    estado['acum_mkt'] += r_mkt
    estado['acum_ops'] += r_ops
    estado['historico'].append({
        "Semana": periodo,
        "Promoción": P, "Anuncio": A, "Exhibición": E,
        "Delta_n": delta_n, "h_reg": h_reg, "h_ext": h_ext,
        "Trabajadores": n,
        "Producción": produccion,
        "Demanda": demanda,
        "Ventas": ventas,
        "Inventario": nuevo_inv,
        "Faltantes": faltantes,
        "W": W,
        "U_MKT": round(r_mkt, 2),
        "C_OPS": round(r_ops, 2)
    })

    st.session_state.periodo += 1
    if st.session_state.periodo > T:
        st.success("✅ Simulación completada")
        df = pd.DataFrame(estado['historico'])
        st.dataframe(df)

        datos = pd.DataFrame([{k: st.session_state[k] for k in ["correo", "turno", "duo", "rol"]}])
        datos_repetidos = pd.concat([datos] * len(df), axis=0).reset_index(drop=True)
        final = pd.concat([datos_repetidos, df], axis=1)

        st.download_button("⬇️ Descargar resultados", final.to_csv(index=False), "resultados_simulacion.csv")
        st.metric("Utilidad acumulada MKT", f"${round(estado['acum_mkt'],2)}")
        st.metric("Costo acumulado OPS", f"${round(estado['acum_ops'],2)}")
        st.metric("Utilidad global", f"${round(estado['acum_mkt'] + estado['acum_ops'],2)}")
        st.stop()
    else:
        st.rerun()



