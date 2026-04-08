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
# Constantes da planilha
# -------------------------------
SHEET_ID = "15l7nHq5TmaU-IMQb9T-C07TLaogAEhbM-3GOQGikmkY"
WORKSHEET_NAME = "Drops"
COLUMNS = ["Drop", "Data", "Membros", "Pago"]


# -------------------------------
# Função de conexão com Google Sheets
# -------------------------------
@st.cache_resource
def get_sheet():
    """Autentica e retorna a worksheet (aba) do Google Sheets."""
    # No Streamlit Cloud, você deve adicionar os segredos no formato:
    # st.secrets["gcp_service_account"] = { ... conteúdo do JSON ... }
    # Ou para testes locais, carregue de um arquivo.
    try:
        # Tenta carregar do st.secrets (recomendado para produção)
        cred_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(
            cred_dict,
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
            ],
        )
    except (KeyError, FileNotFoundError):
        # Fallback para desenvolvimento local: arquivo credentials.json
        with open("credentials.json", "r") as f:
            cred_dict = json.load(f)
        creds = Credentials.from_service_account_info(
            cred_dict,
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
            ],
        )

    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID).worksheet(WORKSHEET_NAME)
    return sheet


def load_data():
    """Carrega os dados da planilha para um DataFrame."""
    sheet = get_sheet()
    records = sheet.get_all_records()
    if not records:
        return pd.DataFrame(columns=COLUMNS)
    df = pd.DataFrame(records)
    # Garantir tipos
    df["Data"] = pd.to_datetime(df["Data"]).dt.date
    df["Pago"] = df["Pago"].astype(bool)
    return df


def save_data(df):
    """Substitui todo o conteúdo da planilha pelos dados do DataFrame."""
    sheet = get_sheet()
    # Prepara os dados: converter data para string ISO e bool para string
    data_to_save = df.copy()
    data_to_save["Data"] = data_to_save["Data"].astype(str)
    data_to_save["Pago"] = data_to_save["Pago"].astype(str)
    # Converte para lista de listas (incluindo cabeçalho)
    valores = [COLUMNS] + data_to_save.values.tolist()
    sheet.clear()
    sheet.update(range_name="A1", values=valores, value_input_option="USER_ENTERED")


def get_all_members(df):
    """Extrai todos os membros únicos da coluna Membros."""
    members = set()
    for membros_str in df["Membros"].dropna():
        for m in membros_str.split(","):
            m = m.strip()
            if m:
                members.add(m)
    return sorted(members)


def filter_by_members(df, selected_members):
    """Filtra linhas onde pelo menos um membro selecionado está presente."""
    if not selected_members:
        return df
    mask = df["Membros"].apply(
        lambda x: (
            any(m in x.split(",") for m in selected_members) if pd.notna(x) else False
        )
    )
    return df[mask]


# -------------------------------
# Carregar dados iniciais
# -------------------------------
if "df" not in st.session_state:
    try:
        st.session_state.df = load_data()
    except Exception as e:
        st.error(f"Erro ao conectar com Google Sheets: {e}")
        st.stop()

# -------------------------------
# Formulário de inserção
# -------------------------------
with st.expander("➕ Inserir novo drop", expanded=False):
    with st.form("inserir_drop"):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            drop_name = st.text_input("Drop *", key="new_drop")
        with col2:
            data = st.date_input("Data *", value=datetime.today(), key="new_data")
        with col3:
            membros_str = st.text_input(
                "Membros (separados por vírgula) *",
                placeholder="ex: Godz, Avril, Gu",
                key="new_membros",
            )
        with col4:
            pago = st.checkbox("Pago?", key="new_pago")

        submitted = st.form_submit_button("Salvar")
        if submitted:
            if not drop_name or not membros_str:
                st.error("Os campos Drop e Membros são obrigatórios.")
            else:
                nova_linha = pd.DataFrame(
                    [
                        {
                            "Drop": drop_name,
                            "Data": data,
                            "Membros": membros_str,
                            "Pago": pago,
                        }
                    ]
                )
                st.session_state.df = pd.concat(
                    [st.session_state.df, nova_linha], ignore_index=True
                )
                save_data(st.session_state.df)
                st.success("Drop adicionado com sucesso!")
                st.rerun()

# -------------------------------
# Filtros
# -------------------------------
st.subheader("🔍 Visualizar e filtrar dados")
if st.session_state.df.empty:
    st.info("Nenhum dado ainda. Use o formulário acima para adicionar drops.")
    st.stop()

all_drops = sorted(st.session_state.df["Drop"].dropna().unique())
all_members = get_all_members(st.session_state.df)

col_f1, col_f2 = st.columns(2)
with col_f1:
    selected_drops = st.multiselect(
        "Filtrar por Drop", options=all_drops, key="filter_drop"
    )
with col_f2:
    selected_members_filter = st.multiselect(
        "Filtrar por Membro", options=all_members, key="filter_member"
    )

# Aplicar filtros
df_filtered = st.session_state.df.copy()
if selected_drops:
    df_filtered = df_filtered[df_filtered["Drop"].isin(selected_drops)]
if selected_members_filter:
    df_filtered = filter_by_members(df_filtered, selected_members_filter)

# Ordenar por Data (mais antiga primeiro)
df_filtered = df_filtered.sort_values(by="Data", ascending=True)

# -------------------------------
# Exibição da tabela editável (apenas Pago)
# -------------------------------
st.markdown("### Tabela de drops")

column_config = {
    "Drop": st.column_config.TextColumn("Drop", disabled=True),
    "Data": st.column_config.DateColumn("Data", disabled=True),
    "Membros": st.column_config.TextColumn("Membros", disabled=True),
    "Pago": st.column_config.CheckboxColumn("Pago", disabled=False),
}

edited_df = st.data_editor(
    df_filtered,
    column_config=column_config,
    use_container_width=True,
    hide_index=True,
    key="data_editor",
)

col_save1, col_save2 = st.columns([1, 5])
with col_save1:
    if st.button("💾 Salvar alterações na coluna Pago"):
        # Atualizar os valores de Pago no DataFrame original
        for idx in edited_df.index:
            original_idx = df_filtered.index[idx]
            if original_idx in st.session_state.df.index:
                st.session_state.df.at[original_idx, "Pago"] = edited_df.at[idx, "Pago"]
        save_data(st.session_state.df)
        st.success("Alterações salvas no Google Sheets!")
        st.rerun()
