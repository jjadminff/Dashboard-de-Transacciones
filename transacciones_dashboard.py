import imaplib
import email
import re
import pandas as pd
from datetime import datetime, date
import streamlit as st
import matplotlib.pyplot as plt
import altair as alt
from bs4 import BeautifulSoup

# CONFIGURACIÓN
IMAP_HOST = 'imap.gmail.com'
USUARIO = 'jjtransacciones@gmail.com'
PASSWORD = st.secrets["gmail_password"]
MAILBOX = 'inbox'

LIMITE_SEMANAL = 175000

# --- FUNCIONES AUXILIARES ---
def normalize_number_text(s):
    s = s.strip()
    if '.' in s and ',' in s:
        if s.rfind(',') > s.rfind('.'):
            s = s.replace('.', '').replace(',', '.')
        else:
            s = s.replace(',', '')
    elif ',' in s:
        if re.match(r'^\d{1,3}(?:[\d.]*\d)?\,\d{2}$', s):
            s = s.replace('.', '').replace(',', '.')
        else:
            s = s.replace(',', '')
    else:
        parts = s.split('.')
        if len(parts) > 1 and len(parts[-1]) == 2:
            s = ''.join(parts[:-1]).replace('.', '') + '.' + parts[-1]
        else:
            s = s.replace('.', '')
    return s

def asignar_categoria(texto, categorias):
    texto = str(texto).lower()
    for cat, keywords in categorias.items():
        if any(k.lower() in texto for k in keywords):
            return cat
    return 'Otros'

# --- CONEXIÓN IMAP ---
mail = imaplib.IMAP4_SSL(IMAP_HOST)
mail.login(USUARIO, PASSWORD)
mail.select(MAILBOX)

# --- LEER CORREOS ---
status, mensajes = mail.search(None, '(ALL)')
data = []

hoy = date.today()
mes_actual = hoy.month
anio_actual = hoy.year

# 🔥 Regex más tolerante
currency_pat = re.compile(r'(CRC|₡|USD|\$)\s*([\d.,]+)', re.IGNORECASE)

for num in mensajes[0].split():
    status, msg_data = mail.fetch(num, '(RFC822)')
    msg = email.message_from_bytes(msg_data[0][1])
    fecha_correo = email.utils.parsedate_to_datetime(msg['Date']).date()

    from_ = msg['From'].lower() if msg['From'] else ''
    subject = msg['Subject'].lower() if msg['Subject'] else ''

    # FILTRO PROMOS
    if any(x in subject for x in ["promoción", "sorteo", "ganador", "campaña"]) or \
       any(x in from_ for x in ["scotiabankca.net", "marketing", "newsletter"]):
        continue

    body = ""

    # 🔥 SOPORTE HTML + TEXT
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            try:
                payload = part.get_payload(decode=True).decode(errors='ignore')
            except:
                continue

            if content_type == "text/plain":
                body += payload
            elif content_type == "text/html":
                soup = BeautifulSoup(payload, "html.parser")
                body += soup.get_text()
    else:
        body = msg.get_payload(decode=True).decode(errors='ignore')

    # 🔥 Normalizar texto
    texto = body.replace('\n', ' ').replace('\xa0', ' ')

    # 🔥 Buscar montos en todo el texto
    for m in currency_pat.finditer(texto):
        moneda_raw = m.group(1)
        valor_raw = m.group(2)

        limpio = normalize_number_text(valor_raw)

        try:
            monto = float(limpio)
        except:
            continue

        tipo_moneda = 'USD' if moneda_raw.strip().upper() in ['USD', '$'] else 'CRC'

        # FILTRO: solo mes actual
        if fecha_correo.month != mes_actual or fecha_correo.year != anio_actual:
            continue

        if 0 < monto < 10000000:
            data.append({
                'fecha': fecha_correo,
                'monto': monto,
                'moneda': tipo_moneda,
                'detalle': texto[:200]
            })

mail.logout()

# --- DATAFRAME SEGURO ---
if not data:
    st.warning("No se encontraron montos válidos en el mes en curso.")
    st.stop()

df = pd.DataFrame(data)

# --- FECHAS ---
df['fecha'] = pd.to_datetime(df['fecha'])
df['mes'] = df['fecha'].dt.to_period('M').astype(str)
df['semana'] = df['fecha'].dt.to_period('W').astype(str)

# --- CATEGORÍAS ---
categorias = {
    'Amazon': ['amazon', 'prime'],
    'Pricesmart': ['pricesmart costa rica'],
    'Supermercado': ['mega super', 'mas x menos', 'fresh market', 'super'],
    'Restaurante': ['didi', 'burger', 'restaurant', 'food'],
    'Gasolina': ['gasolina'],
    'Farmacia': ['farmacia'],
    'Otros': []
}

df['categoria'] = df['detalle'].apply(lambda x: asignar_categoria(x, categorias))

# --- RESÚMENES ---
sum_diaria = df.groupby(['fecha','moneda'])['monto'].sum().unstack(fill_value=0)
sum_semanal = df.groupby(['semana','moneda'])['monto'].sum().unstack(fill_value=0)
sum_mensual = df.groupby(['mes','moneda'])['monto'].sum().unstack(fill_value=0)
sum_categoria_mensual = df.groupby(['mes','categoria','moneda'])['monto'].sum().reset_index()

# --- DASHBOARD ---
st.title("💳 Transacciones Tarjeta de Credito JJ")

st.subheader("Detalle de transacciones")
st.dataframe(df[['fecha','monto','moneda','detalle']])

st.subheader("Suma diaria")
st.dataframe(sum_diaria)

st.subheader("Suma semanal")
st.dataframe(sum_semanal)

st.subheader("Suma mensual")
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
