import json
import time as time_module
from datetime import datetime, time, timedelta, timezone

import pandas as pd
import streamlit as st
import gspread
from google.oauth2 import service_account

# CONFIG
SPREADSHEET_ID = "15l7nHq5TmaU-IMQb9T-C07TLaogAEhbM-3GOQGikmkY"
WORKSHEET_NAME = "Minis"

BRASIL_TIMEZONE = timezone(timedelta(hours=-3))

# CACHE GLOBAL
cached_data = None
last_read_time = None


# 🔥 AUTENTICAÇÃO
@st.cache_resource
def get_google_sheets_client():
    info = json.loads(st.secrets["gcp_service_account"]["json"])

    credentials = service_account.Credentials.from_service_account_info(
        info,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ],
    )

    return gspread.authorize(credentials)


# 🔥 CRIA ABA AUTOMATICAMENTE
def get_or_create_worksheet(sh, worksheet_name):
    abas = [ws.title for ws in sh.worksheets()]

    if worksheet_name not in abas:
        worksheet = sh.add_worksheet(title=worksheet_name, rows="100", cols="20")
        st.warning(f"Aba '{worksheet_name}' criada automaticamente!")
    else:
        worksheet = sh.worksheet(worksheet_name)

    return worksheet


# 🔥 LOAD DATA
def load_data(force_reload=False):
    global last_read_time, cached_data

    if not force_reload and cached_data is not None and last_read_time:
        time_since_last_read = (datetime.now() - last_read_time).total_seconds()
        if time_since_last_read < 300:
            return cached_data

    try:
        gc = get_google_sheets_client()
        sh = gc.open_by_key(SPREADSHEET_ID)
        worksheet = get_or_create_worksheet(sh, WORKSHEET_NAME)

        data = worksheet.get_all_records()
        df = pd.DataFrame(data)

        if df.empty:
            return pd.DataFrame()

        time_columns = ["Nasce às", "Timer", "Prox."]

        for col in time_columns:
            if col in df.columns:
                df[col] = df[col].replace(["", "None", "null", "Null", "NONE"], None)

                def convert_to_time(x):
                    if pd.isna(x) or x is None:
                        return None
                    try:
                        if isinstance(x, str):
                            x = x.strip()
                            if ":" in x:
                                parts = x.split(":")
                                if len(parts) >= 2:
                                    hour = int(parts[0])
                                    minute = int(parts[1])
                                    if 0 <= hour < 24 and 0 <= minute < 60:
                                        return time(hour, minute)
                        elif isinstance(x, datetime):
                            return x.time()
                    except:
                        return None
                    return None

                df[col] = df[col].apply(convert_to_time)

        cached_data = df
        last_read_time = datetime.now()
        return df

    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return pd.DataFrame()


# 🔥 SAVE DATA
def save_data(df):
    try:
        gc = get_google_sheets_client()
        sh = gc.open_by_key(SPREADSHEET_ID)
        worksheet = get_or_create_worksheet(sh, WORKSHEET_NAME)

        df_to_save = df.copy()
        time_columns = ["Nasce às", "Timer", "Prox."]

        for col in time_columns:
            if col in df_to_save.columns:
                df_to_save[col] = df_to_save[col].apply(
                    lambda x: (
                        x.strftime("%H:%M")
                        if isinstance(x, time) and pd.notnull(x)
                        else x if pd.notnull(x) else ""
                    )
                )

        df_to_save = df_to_save.fillna("")
        data = [df_to_save.columns.tolist()] + df_to_save.values.tolist()

        worksheet.update(data, value_input_option="USER_ENTERED")

        st.success("✅ Alterações salvas com sucesso!")

        global cached_data
        cached_data = df.copy()

        return True

    except Exception as e:
        st.error(f"Erro ao salvar dados: {e}")
        return False


# 🔥 CÁLCULOS
def calcular_segundos_restantes(nasce_as):
    if not nasce_as or not isinstance(nasce_as, time):
        return 10800

    try:
        agora_utc = datetime.now(timezone.utc)
        agora_local = datetime.now(BRASIL_TIMEZONE)

        morte_gmt0 = datetime.combine(agora_utc.date(), nasce_as).replace(
            tzinfo=timezone.utc
        )

        if morte_gmt0 > agora_utc:
            morte_gmt0 -= timedelta(days=1)

        respawn_gmt0 = morte_gmt0 + timedelta(hours=3)
        respawn_local = respawn_gmt0.astimezone(BRASIL_TIMEZONE)

        segundos = int((respawn_local - agora_local).total_seconds())
        return segundos if segundos > 0 else 0

    except:
        return 10800


def calcular_tempo_restante_ajustado(nasce_as):
    segundos = calcular_segundos_restantes(nasce_as)

    if segundos <= 0:
        return "VIVO"

    horas = segundos // 3600
    minutos = (segundos % 3600) // 60
    segundos_rest = segundos % 60

    return f"{horas:02d}:{minutos:02d}:{segundos_rest:02d}"


def calcular_horario_respawn_local(nasce_as):
    if not nasce_as or not isinstance(nasce_as, time):
        return "--:--"

    try:
        agora_utc = datetime.now(timezone.utc)

        morte_gmt0 = datetime.combine(agora_utc.date(), nasce_as).replace(
            tzinfo=timezone.utc
        )

        if morte_gmt0 > agora_utc:
            morte_gmt0 -= timedelta(days=1)

        respawn_gmt0 = morte_gmt0 + timedelta(hours=3)
        respawn_local = respawn_gmt0.astimezone(BRASIL_TIMEZONE)

        return respawn_local.strftime("%H:%M")

    except:
        return "--:--"


# UI
st.set_page_config(page_title="Mini-Boss Timer - Myth of Yggdrasil", layout="wide")
st.title("Mini-Boss Timer :blue[MoY]")
st.divider()

# INIT SESSION
if "dados_locais" not in st.session_state:
    st.session_state.dados_locais = load_data()

if "time_versions" not in st.session_state:
    st.session_state.time_versions = {}

# 🔥 AUTO UPDATE CONFIG
with st.sidebar:
    update_options = st.radio(
        "Atualização automática",
        ["Desligado", "1 segundo", "5 segundos", "30 segundos"],
        index=0,
    )

    update_interval = {
        "Desligado": 0,
        "1 segundo": 1,
        "5 segundos": 5,
        "30 segundos": 30,
    }[update_options]

# 🔥 AUTO REFRESH (CORRIGIDO)
if update_interval > 0:
    next_update = datetime.now() + timedelta(seconds=update_interval)
    st.caption(f"⏰ Próxima atualização: {next_update.strftime('%H:%M:%S')}")

    time_module.sleep(update_interval)
    st.rerun()
