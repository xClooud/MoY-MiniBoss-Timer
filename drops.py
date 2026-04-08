import json
from datetime import datetime

import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials

# -------------------------------
# Configuração da página
# -------------------------------
st.set_page_config(page_title="Planilha de Drops - Google Sheets", layout="wide")
st.title("📋 Planilha de Drops")

# -------------------------------
# Constantes
# -------------------------------
SHEET_ID = "15l7nHq5TmaU-IMQb9T-C07TLaogAEhbM-3GOQGikmkY"
WORKSHEET_NAME = "Drops"
COLUMNS = ["Drop", "Data", "Membros", "Pago"]

# -------------------------------
# Conexão com Google Sheets
# -------------------------------
@st.cache_resource
def get_client():
    info = json.loads(st.secrets["gcp_service_account"]["json"])

    creds = Credentials.from_service_account_info(
        info,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ],
    )

    return gspread.authorize(creds)


def get_or_create_worksheet():
    client = get_client()
    sh = client.open_by_key(SHEET_ID)

    abas = [ws.title for ws in sh.worksheets()]

    if WORKSHEET_NAME not in abas:
        worksheet = sh.add_worksheet(title=WORKSHEET_NAME, rows="100", cols="20")
        worksheet.append_row(COLUMNS)
        st.warning(f"Aba '{WORKSHEET_NAME}' criada automaticamente!")
    else:
        worksheet = sh.worksheet(WORKSHEET_NAME)

        # 🔥 garante cabeçalho
        values = worksheet.get_all_values()
        if not values:
            worksheet.append_row(COLUMNS)

    return worksheet


# -------------------------------
# DATA
# -------------------------------
def load_data():
    sheet = get_or_create_worksheet()

    records = sheet.get_all_records()
    if not records:
        return pd.DataFrame(columns=COLUMNS)

    df = pd.DataFrame(records)

    # 🔥 segurança de tipos
    if "Data" in df.columns:
        df["Data"] = pd.to_datetime(df["Data"], errors="coerce").dt.date

    if "Pago" in df.columns:
        df["Pago"] = df["Pago"].astype(str).str.lower().isin(["true", "1", "yes"])

    return df


def save_data(df):
    sheet = get_or_create_worksheet()

    df_to_save = df.copy()

    # 🔥 conversões seguras
    df_to_save["Data"] = df_to_save["Data"].apply(
    lambda x: x.strftime("%d/%m/%Y") if pd.notnull(x) else ""
)
    df_to_save["Pago"] = df_to_save["Pago"].astype(str)

    valores = [COLUMNS] + df_to_save.values.tolist()

    sheet.clear()
    sheet.update("A1", valores, value_input_option="USER_ENTERED")


# -------------------------------
# UTILS
# -------------------------------
def get_all_members(df):
    members = set()
    for membros_str in df["Membros"].dropna():
        for m in str(membros_str).split(","):
            m = m.strip()
            if m:
                members.add(m)
    return sorted(members)


def filter_by_members(df, selected_members):
    if not selected_members:
        return df

    return df[
        df["Membros"].apply(
            lambda x: any(m in str(x).split(",") for m in selected_members)
        )
    ]


# -------------------------------
# LOAD INICIAL
# -------------------------------
if "df" not in st.session_state:
    try:
        st.session_state.df = load_data()
    except Exception as e:
        st.error(f"Erro ao conectar com Google Sheets: {e}")
        st.stop()

# -------------------------------
# FORM
# -------------------------------
with st.expander("➕ Inserir novo drop"):
    with st.form("form"):
        col1, col2, col3, col4 = st.columns(4)

        drop = col1.text_input("Drop *")
        data = col2.date_input("Data *", value=datetime.today())
        membros = col3.text_input("Membros * (separados por vírgula)")
        pago = col4.checkbox("Pago")

        if st.form_submit_button("Salvar"):
            if not drop or not membros:
                st.error("Preencha os campos obrigatórios.")
            else:
                nova = pd.DataFrame(
                    [[drop, data, membros, pago]], columns=COLUMNS
                )
                st.session_state.df = pd.concat(
                    [st.session_state.df, nova], ignore_index=True
                )
                save_data(st.session_state.df)
                st.success("Salvo!")
                st.rerun()

# -------------------------------
# FILTROS
# -------------------------------
st.subheader("🔍 Filtros")

if st.session_state.df.empty:
    st.info("Sem dados ainda.")
    st.stop()

all_drops = sorted(st.session_state.df["Drop"].dropna().unique())
all_members = get_all_members(st.session_state.df)

col1, col2 = st.columns(2)
selected_drops = col1.multiselect("Drop", all_drops)
selected_members = col2.multiselect("Membros", all_members)

df_filtered = st.session_state.df.copy()

if selected_drops:
    df_filtered = df_filtered[df_filtered["Drop"].isin(selected_drops)]

if selected_members:
    df_filtered = filter_by_members(df_filtered, selected_members)

df_filtered = df_filtered.sort_values(by="Data")

# -------------------------------
# TABELA
# -------------------------------
st.markdown("### Tabela")

edited_df = st.data_editor(
    df_filtered,
    column_config={
        "Drop": st.column_config.TextColumn(disabled=True),
        "Data": st.column_config.DateColumn(disabled=True),
        "Membros": st.column_config.TextColumn(disabled=True),
        "Pago": st.column_config.CheckboxColumn(),
    },
    use_container_width=True,
    hide_index=True,
)

if st.button("💾 Salvar alterações"):
    for idx in edited_df.index:
        original_idx = df_filtered.index[idx]
        st.session_state.df.at[original_idx, "Pago"] = edited_df.at[idx, "Pago"]

    save_data(st.session_state.df)
    st.success("Atualizado!")
    st.rerun()
