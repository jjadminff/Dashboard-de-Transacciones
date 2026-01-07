import imaplib
import email
import re
import pandas as pd
from datetime import datetime, date
import streamlit as st
import altair as alt

# ================= CONFIGURACIÓN =================
IMAP_HOST = 'imap.gmail.com'
USUARIO = 'jjtransacciones@gmail.com'
PASSWORD = st.secrets["gmail_password"]
MAILBOX = 'inbox'

FROM_VALIDO = 'alertas@davibank.cr'
ASUNTO_CLAVE = 'alerta transaccion tarjeta'
FRASE_CLAVE = 'davibank le notifica que la transaccion realizada'

# ================= FUNCIONES AUX =================
def normalize_text(s: str) -> str:
    return (
        s.lower()
        .replace('á','a')
        .replace('é','e')
        .replace('í','i')
        .replace('ó','o')
        .replace('ú','u')
    )

def normalize_number_text(s):
    return s.replace(',', '')

def asignar_categoria(texto, categorias):
    texto = str(texto).lower()
    for cat, keywords in categorias.items():
        if any(k in texto for k in keywords):
            return cat
    return 'Otros'

# ================= REGEX DAVIBANK =================
PATRON_TRANSACCION = re.compile(
    r'DAVIbank le notifica que la transacción realizada en\s+'
    r'(?P<comercio>.+?),\s+el día\s+'
    r'(?P<fecha>\d{2}/\d{2}/\d{4})\s+a\s+'
    r'(?P<hora>\d{2}:\d{2}\s+[AP]M).*?'
    r'por\s+(?P<moneda>CRC|USD)\s+'
    r'(?P<monto>\d{1,3}(?:,\d{3})*(?:\.\d{2}))',
    re.IGNORECASE | re.DOTALL
)

# ================= CONEXIÓN IMAP =================
mail = imaplib.IMAP4_SSL(IMAP_HOST)
mail.login(USUARIO, PASSWORD)
mail.select(MAILBOX)

status, mensajes = mail.search(None, '(ALL)')
data = []

hoy = date.today()
mes_actual = hoy.month
anio_actual = hoy.year

# ================= LECTURA DE CORREOS =================
for num in mensajes[0].split():
    status, msg_data = mail.fetch(num, '(RFC822)')
    msg = email.message_from_bytes(msg_data[0][1])

    # ---------- FILTRO FROM ----------
    from_raw = msg.get('From', '')
    if FROM_VALIDO not in from_raw.lower():
        continue

    # ---------- FILTRO SUBJECT ----------
    subject = normalize_text(msg.get('Subject', ''))
    if ASUNTO_CLAVE not in subject:
        continue

    # ---------- BODY ----------
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() in ("text/plain", "text/html"):
                body += part.get_payload(decode=True).decode(errors='ignore')
    else:
        body = msg.get_payload(decode=True).decode(errors='ignore')

    body_norm = normalize_text(body)

    if FRASE_CLAVE not in body_norm:
        continue

    if 'fue aprobada' not in body_norm:
        continue

    match = PATRON_TRANSACCION.search(body)
    if not match:
        continue

    fecha_tx = datetime.strptime(
        f"{match.group('fecha')} {match.group('hora')}",
        "%d/%m/%Y %I:%M %p"
    ).date()

    if fecha_tx.month != mes_actual or fecha_tx.year != anio_actual:
        continue

    monto = float(normalize_number_text(match.group('monto')))
    moneda = match.group('moneda').upper()
    comercio = match.group('comercio').strip()

    if 0 < monto < 10_000_000:
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
    st.warning("No se encontraron transacciones DAVIbank en el mes actual.")
    st.stop()

st.subheader("Detalle de transacciones")
st.dataframe(df[['fecha','monto','moneda','detalle']])

df['fecha'] = pd.to_datetime(df['fecha'])
df['mes'] = df['fecha'].dt.to_period('M').astype(str)

# ================= CATEGORÍAS =================
categorias = {
    'Amazon': ['amazon', 'prime'],
    'Pricesmart': ['pricesmart'],
    'Supermercado': ['super', 'market'],
    'Restaurante': ['restaurant', 'food', 'cafe', 'soda'],
    'Gasolina': ['estacion'],
    'Carnes': ['carnes'],
    'Farmacia': ['farmacia'],
    'Otros': []
}

df['categoria'] = df['detalle'].apply(lambda x: asignar_categoria(x, categorias))

# ================= RESÚMENES =================
sum_diaria = df.groupby(['fecha','moneda'])['monto'].sum().unstack(fill_value=0)
sum_mensual = df.groupby(['mes','moneda'])['monto'].sum().unstack(fill_value=0)
sum_categoria_mensual = df.groupby(['mes','categoria','moneda'])['monto'].sum().reset_index()

# ================= DASHBOARD =================
st.title("💳 Transacciones Tarjeta de Crédito JJ")

st.subheader("Suma diaria total (por moneda)")
st.dataframe(sum_diaria)

st.subheader("Suma mensual total (por moneda)")
st.dataframe(sum_mensual)

st.subheader("Resumen mensual por categoría (por moneda)")
st.dataframe(sum_categoria_mensual)

chart = alt.Chart(sum_categoria_mensual).mark_bar().encode(
    x='categoria:N',
    y='monto:Q',
    color='moneda:N',
    column='mes:N'
)
st.altair_chart(chart, use_container_width=True)

# ================= DÍA MAYOR GASTO =================
st.subheader("📈 Día con mayor gasto por moneda")

if 'CRC' in sum_diaria:
    d = sum_diaria['CRC'].idxmax()
    st.write(f"Mayor gasto en CRC: ₡{sum_diaria.loc[d,'CRC']:,.2f} el día {d.date()}")

if 'USD' in sum_diaria:
    d = sum_diaria['USD'].idxmax()
    st.write(f"Mayor gasto en USD: ${sum_diaria.loc[d,'USD']:,.2f} el día {d.date()}")
