import imaplib
import email
import re
import pandas as pd
from datetime import datetime, date
import streamlit as st
import unicodedata
import matplotlib.pyplot as plt
import altair as alt

# ================= CONFIG =================
IMAP_HOST = 'imap.gmail.com'
USUARIO = 'jjtransacciones@gmail.com'
PASSWORD = st.secrets["gmail_password"]
MAILBOX = 'inbox'

# ================= UTILS =================
def normalize(text):
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    return text.lower()

def asignar_categoria(texto, categorias):
    texto = texto.lower()
    for cat, keys in categorias.items():
        if any(k in texto for k in keys):
            return cat
    return 'Otros'

# ================= REGEX (REENVIADO) =================
PATRON = re.compile(
    r'davibank le notifica que la transaccion realizada en\s+'
    r'(?P<comercio>.+?),\s+el dia\s+'
    r'(?P<fecha>\d{2}/\d{2}/\d{4})\s+a\s+'
    r'(?P<hora>\d{2}:\d{2}\s+[ap]m).*?'
    r'por\s+(?P<moneda>crc|usd)\s+'
    r'(?P<monto>\d{1,3}(?:,\d{3})*(?:\.\d{2}))',
    re.DOTALL
)

# ================= IMAP =================
mail = imaplib.IMAP4_SSL(IMAP_HOST)
mail.login(USUARIO, PASSWORD)
mail.select(MAILBOX)

status, mensajes = mail.search(None, 'ALL')
data = []

hoy = date.today()

for num in mensajes[0].split():
    _, msg_data = mail.fetch(num, '(RFC822)')
    msg = email.message_from_bytes(msg_data[0][1])

    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                body += part.get_payload(decode=True).decode(errors='ignore')
    else:
        body = msg.get_payload(decode=True).decode(errors='ignore')

    body_norm = normalize(body)

    # 🔒 FILTRO FUERTE: solo correos reenviados de DAVIbank
    if 'from: alertas@davibank.cr' not in body_norm:
        continue

    match = PATRON.search(body_norm)
    if not match:
        continue

    fecha_tx = datetime.strptime(
        f"{match.group('fecha')} {match.group('hora')}",
        "%d/%m/%Y %I:%M %p"
    ).date()

    if fecha_tx.month != hoy.month or fecha_tx.year != hoy.year:
        continue

    monto = float(match.group('monto').replace(',', ''))
    moneda = match.group('moneda').upper()
    comercio = match.group('comercio').strip()

    data.append({
        'fecha': fecha_tx,
        'monto': monto,
        'moneda': moneda,
        'detalle': comercio
    })

mail.logout()

# ================= DATAFRAME =================
df = pd.DataFrame(data)
if df.empty:
    st.error("❌ No se encontraron transacciones DAVIbank en el mes actual.")
    st.stop()

st.success(f"✅ {len(df)} transacciones DAVIbank detectadas")
st.dataframe(df)

# ================= RESTO IGUAL =================
df['fecha'] = pd.to_datetime(df['fecha'])
df['mes'] = df['fecha'].dt.to_period('M').astype(str)

categorias = {
    'Supermercado': ['soda', 'super', 'market'],
    'Restaurante': ['restaurant', 'food', 'cafe'],
    'Gasolina': ['estacion'],
    'Farmacia': ['farmacia'],
    'Otros': []
}

df['categoria'] = df['detalle'].apply(lambda x: asignar_categoria(x, categorias))

sum_diaria = df.groupby(['fecha','moneda'])['monto'].sum().unstack(fill_value=0)
st.dataframe(sum_diaria)
