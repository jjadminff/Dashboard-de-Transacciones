import imaplib
import email
import re
import pandas as pd
from datetime import datetime, date
import streamlit as st
import matplotlib.pyplot as plt
import altair as alt
from bs4 import BeautifulSoup

# DEBUG VERSION
st.write("VERSION FINAL 4")

# CONFIGURACIÓN
IMAP_HOST = 'imap.gmail.com'
USUARIO = 'jjtransacciones@gmail.com'
PASSWORD = st.secrets["gmail_password"]
MAILBOX = 'inbox'

LIMITE_SEMANAL = 175000

# --- FUNCIONES ---
def normalize_number_text(s):
    s = s.strip()
    if '.' in s and ',' in s:
        if s.rfind(',') > s.rfind('.'):
            s = s.replace('.', '').replace(',', '.')
        else:
            s = s.replace(',', '')
    elif ',' in s:
        s = s.replace('.', '').replace(',', '.')
    else:
        s = s.replace('.', '')
    return s

def asignar_categoria(texto, categorias):
    texto = str(texto).lower()
    for cat, keywords in categorias.items():
        if any(k.lower() in texto for k in keywords):
            return cat
    return 'Otros'

# --- IMAP ---
mail = imaplib.IMAP4_SSL(IMAP_HOST)
mail.login(USUARIO, PASSWORD)
mail.select(MAILBOX)

status, mensajes = mail.search(None, '(ALL)')
data = []

hoy = date.today()
mes_actual = hoy.month
anio_actual = hoy.year

currency_pat = re.compile(r'(CRC|₡|USD|\$)\s*([\d.,]+)', re.IGNORECASE)

for num in mensajes[0].split():
    status, msg_data = mail.fetch(num, '(RFC822)')
    msg = email.message_from_bytes(msg_data[0][1])

    try:
        fecha_correo = email.utils.parsedate_to_datetime(msg['Date']).date()
    except:
        continue

    from_ = msg['From'].lower() if msg['From'] else ''
    subject = msg['Subject'].lower() if msg['Subject'] else ''

    # FILTRO PROMOS
    if any(x in subject for x in ["promoción", "sorteo", "ganador", "campaña"]) or \
       any(x in from_ for x in ["marketing", "newsletter"]):
        continue

    body = ""

    if msg.is_multipart():
        for part in msg.walk():
            try:
                payload = part.get_payload(decode=True).decode(errors='ignore')
            except:
                continue

            if part.get_content_type() == "text/plain":
                body += payload
            elif part.get_content_type() == "text/html":
                soup = BeautifulSoup(payload, "html.parser")
                body += soup.get_text()
    else:
        try:
            body = msg.get_payload(decode=True).decode(errors='ignore')
        except:
            continue

    # 🔥 NORMALIZAR TEXTO
    texto = body.replace('\n', ' ').replace('\xa0', ' ')

    # 🔥 EXTRAER MONTOS
    for m in currency_pat.finditer(texto):
        moneda_raw = m.group(1)
        valor_raw = m.group(2)

        limpio = normalize_number_text(valor_raw)

        try:
            monto = float(limpio)
        except:
            continue

        if fecha_correo.month != mes_actual or fecha_correo.year != anio_actual:
            continue

        tipo_moneda = 'USD' if moneda_raw.strip().upper() in ['USD', '$'] else 'CRC'

        if 0 < monto < 10000000:
            data.append({
                'fecha': fecha_correo,
                'monto': monto,
                'moneda': tipo_moneda,
                'detalle': texto[:200]
            })

mail.logout()

# DEBUG
st.write("DATA LEN:", len(data))

# --- CONTROL DURO ---
if len(data) == 0:
    st.warning("No se encontraron montos válidos en el mes en curso.")
    st.stop()

# --- DATAFRAME ---
df = pd.DataFrame(data)

# 🔥 PROTECCIÓN EXTRA
if df is None or df.empty or 'fecha' not in df.columns:
    st.error("DF inválido - sin datos o sin columna fecha")
    st.stop()

# --- FECHAS ---
try:
    df['fecha'] = pd.to_datetime(df['fecha'])
except Exception as e:
    st.error(f"Error convirtiendo fechas: {e}")
    st.stop()

df['mes'] = df['fecha'].dt.to_period('M').astype(str)
df['semana'] = df['fecha'].dt.to_period('W').astype(str)

# --- CATEGORÍAS ---
categorias = {
    'Amazon': ['amazon', 'prime'],
    'Pricesmart': ['pricesmart'],
    'Supermercado': ['super', 'market'],
    'Restaurante': ['didi', 'burger', 'restaurant'],
    'Gasolina': ['gasolina'],
    'Farmacia': ['farmacia'],
    'Otros': []
}

df['categoria'] = df['detalle'].apply(lambda x: asignar_categoria(x, categorias))

# --- RESÚMENES ---
sum_diaria = df.groupby(['fecha','moneda'])['monto'].sum().unstack(fill_value=0)
sum_semanal = df.groupby(['semana','moneda'])['monto'].sum().unstack(fill_value=0)
sum_mensual = df.groupby(['mes','moneda'])['monto'].sum().unstack(fill_value=0)

# --- UI ---
st.title("💳 Transacciones Tarjeta de Credito JJ")

st.subheader("Detalle")
st.dataframe(df[['fecha','monto','moneda','detalle']])

st.subheader("Diario")
st.dataframe(sum_diaria)

st.subheader("Semanal")
st.dataframe(sum_semanal)

st.subheader("Mensual")
st.dataframe(sum_mensual)

# --- ALERTA ---
ultima_semana = sum_semanal.index.max()
gasto_semana_crc = sum_semanal.loc[ultima_semana, 'CRC'] if 'CRC' in sum_semanal.columns else 0

st.subheader("🚨 Control semanal")

if gasto_semana_crc > LIMITE_SEMANAL:
    st.error(f"⚠️ Te pasaste: ₡{gasto_semana_crc:,.0f}")
elif gasto_semana_crc > LIMITE_SEMANAL * 0.8:
    st.warning(f"⚠️ Cuidado: ₡{gasto_semana_crc:,.0f}")
else:
    st.success(f"✅ Bien: ₡{gasto_semana_crc:,.0f}")
