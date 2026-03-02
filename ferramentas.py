import streamlit as st

import utils  # supondo que o módulo utils exista com as funções

st.title("Ferramentas")

# Criamos duas colunas principais para os cards ficarem lado a lado
col_esq, col_dir = st.columns(2)

# ---------- CARD DA CALCULADORA DE VCT ----------
with col_esq:
    with st.container(border=True):
        st.subheader("Calculadora de VCT")

        # Organiza os inputs em três colunas internas
        col1, col2, col3 = st.columns(3)

        with col1:
            base = st.number_input(
                "VCT Base",
                min_value=0,
            )
            vctFlat = st.number_input(
                "VCT Flat", min_value=0.0, step=0.1, format="%.2f"
            )

        with col2:
            vctPercent = st.number_input("VCT Percentual (%)", min_value=0, step=1)
            int_val = st.number_input("INT", min_value=0, step=1)

        with col3:
            dex = st.number_input("Dex", min_value=0, step=1)
            calcular_vct = st.button("Calcular VCT", key="btn_vct", type="primary")

        if calcular_vct:
            vct = utils.VariableCast(base, vctFlat, vctPercent, int_val, dex)
            st.success(f"VCT restante: **{max(vct, 0):.2f}**")

# ---------- CARD DA CALCULADORA DE HARD DEF ----------
with col_dir:
    with st.container(border=True):
        st.subheader("🛡️ Calculadora de Hard Def")

        # Organiza os inputs em duas colunas internas
        colA, colB = st.columns(2)

        with colA:
            baseDmg = st.number_input("Dano Base", min_value=0, step=1)
            hDef = st.number_input("Hard DEF do Alvo", min_value=0, step=1)

        with colB:
            reducaoFlat = st.number_input("Redução Flat", min_value=0, step=1)
            reducaoPercent = st.number_input(
                "Redução Percentual (%)", min_value=0, step=1
            )

        calcular_def = st.button("Calcular Dano", key="btn_def", type="primary")

        if calcular_def:
            dmg = utils.HardDef(baseDmg, hDef, reducaoFlat, reducaoPercent)
            st.success(f"Dano causado: **{dmg:.2f}**")

with col_esq:
    with st.container(border=True):
        st.subheader("🛡️🪄 Calculadora de Hard MDef")

        # Organiza os inputs em duas colunas internas
        colA1, colB1 = st.columns(2)

        with colA1:
            baseNDmg = st.number_input("Dano Base", min_value=0, step=1, key="magical")
            hMDef = st.number_input("Hard MDEF do Alvo", min_value=0, step=1)

        with colB1:
            reducaoMFlat = st.number_input(
                "Redução Flat", min_value=0, step=1, key="reducao"
            )
            reducaoMPercent = st.number_input(
                "Redução Percentual (%)", min_value=0, step=1, key="reducao_percent"
            )

        calcular_mdef = st.button("Calcular Dano", key="btn_mdef", type="primary")

        if calcular_mdef:
            mdmg = utils.HardDef(baseNDmg, hMDef, reducaoMFlat, reducaoMPercent)
            st.success(f"Dano causado: **{mdmg:.2f}**")
