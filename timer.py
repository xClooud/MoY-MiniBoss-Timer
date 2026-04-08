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

# CACHE
cached_data = None
last_read_time = None


# 🔥 AUTH
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


# 🔥 CREATE SHEET
def get_or_create_worksheet(sh, worksheet_name):
    abas = [ws.title for ws in sh.worksheets()]

    if worksheet_name not in abas:
        worksheet = sh.add_worksheet(title=worksheet_name, rows="100", cols="20")
        st.warning(f"Aba '{worksheet_name}' criada automaticamente!")
    else:
        worksheet = sh.worksheet(worksheet_name)

    return worksheet


# 🔥 LOAD
def load_data(force_reload=False):
    global last_read_time, cached_data

    if not force_reload and cached_data is not None and last_read_time:
        if (datetime.now() - last_read_time).total_seconds() < 300:
            return cached_data

    try:
        gc = get_google_sheets_client()
        sh = gc.open_by_key(SPREADSHEET_ID)
        worksheet = get_or_create_worksheet(sh, WORKSHEET_NAME)

        data = worksheet.get_all_records()
        df = pd.DataFrame(data)

        time_columns = ["Nasce às", "Timer", "Prox."]

        for col in time_columns:
            if col in df.columns:
                df[col] = df[col].replace(
                    ["", "None", "null", "Null", "NONE"], None
                )

                def convert(x):
                    if pd.isna(x):
                        return None
                    try:
                        if isinstance(x, str) and ":" in x:
                            h, m = map(int, x.split(":")[:2])
                            return time(h, m)
                        elif isinstance(x, datetime):
                            return x.time()
                    except:
                        return None
                    return None

                df[col] = df[col].apply(convert)

        cached_data = df
        last_read_time = datetime.now()
        return df

    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return pd.DataFrame()


# 🔥 SAVE
def save_data(df):
    try:
        gc = get_google_sheets_client()
        sh = gc.open_by_key(SPREADSHEET_ID)
        worksheet = get_or_create_worksheet(sh, WORKSHEET_NAME)

        df_to_save = df.copy()

        for col in ["Nasce às", "Timer", "Prox."]:
            if col in df_to_save.columns:
                df_to_save[col] = df_to_save[col].apply(
                    lambda x: x.strftime("%H:%M")
                    if isinstance(x, time)
                    else (x if pd.notnull(x) else "")
                )

        df_to_save = df_to_save.fillna("")
        data = [df_to_save.columns.tolist()] + df_to_save.values.tolist()

        worksheet.update(data, value_input_option="USER_ENTERED")

        st.success("✅ Salvo!")
        return True

    except Exception as e:
        st.error(f"Erro ao salvar dados: {e}")
        return False


# 🔥 CALCULOS
def calcular_segundos_restantes(nasce_as):
    if not isinstance(nasce_as, time):
        return 10800

    try:
        agora_utc = datetime.now(timezone.utc)
        agora_local = datetime.now(BRASIL_TIMEZONE)

        morte = datetime.combine(agora_utc.date(), nasce_as).replace(
            tzinfo=timezone.utc
        )

        if morte > agora_utc:
            morte -= timedelta(days=1)

        respawn = morte + timedelta(hours=3)
        respawn_local = respawn.astimezone(BRASIL_TIMEZONE)

        segundos = int((respawn_local - agora_local).total_seconds())
        return max(segundos, 0)

    except:
        return 10800


def calcular_tempo_restante_ajustado(nasce_as):
    s = calcular_segundos_restantes(nasce_as)
    if s <= 0:
        return "VIVO"
    return f"{s//3600:02d}:{(s%3600)//60:02d}:{s%60:02d}"


def calcular_horario_respawn_local(nasce_as):
    if not isinstance(nasce_as, time):
        return "--:--"

    try:
        agora_utc = datetime.now(timezone.utc)

        morte = datetime.combine(agora_utc.date(), nasce_as).replace(
            tzinfo=timezone.utc
        )

        if morte > agora_utc:
            morte -= timedelta(days=1)

        respawn = morte + timedelta(hours=3)
        return respawn.astimezone(BRASIL_TIMEZONE).strftime("%H:%M")

    except:
        return "--:--"


# UI
st.set_page_config(page_title="Mini-Boss Timer", layout="wide")
st.title("Mini-Boss Timer :blue[MoY]")

# INIT
if "dados_locais" not in st.session_state:
    st.session_state.dados_locais = load_data()

if "time_versions" not in st.session_state:
    st.session_state.time_versions = {}

# SIDEBAR
with st.sidebar:
    update = st.radio(
        "Atualização",
        ["Off", "1s", "5s", "30s"],
        index=0,
    )

    interval = {"Off": 0, "1s": 1, "5s": 5, "30s": 30}[update]

    if st.button("💾 Salvar"):
        save_data(st.session_state.dados_locais)
        st.rerun()

# GRID
mobs = []
for idx, row in st.session_state.dados_locais.iterrows():
    mob = row.to_dict()
    mob["index"] = idx
    mob["segundos"] = calcular_segundos_restantes(mob.get("Nasce às"))
    mobs.append(mob)

mobs.sort(key=lambda x: x["segundos"])

cols = st.columns(6)

for i, mob in enumerate(mobs):
    with cols[i % 6]:
        idx = mob["index"]
        nome = mob.get("Mob", "")
        nasce = mob.get("Nasce às")

        st.markdown(f"**{nome}**")
        st.markdown(calcular_tempo_restante_ajustado(nasce))

        novo = st.time_input(
            "Hora",
            value=nasce if nasce else time(0, 0),
            key=f"{idx}_{st.session_state.time_versions.get(idx,0)}",
        )

        if novo != nasce:
            st.session_state.dados_locais.at[idx, "Nasce às"] = novo
            st.rerun()

# 🔥 AUTO REFRESH CORRIGIDO
if interval > 0:
    time_module.sleep(interval)
    st.rerun()
