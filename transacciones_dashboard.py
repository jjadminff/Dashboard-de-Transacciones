import imaplib
import email
import re
import pandas as pd
from datetime import datetime, date
import streamlit as st
import matplotlib.pyplot as plt
import altair as alt

# ================= CONFIGURACIÓN =================
IMAP_HOST = 'imap.gmail.com'
USUARIO = 'jjtransacciones@gmail.com'
PASSWORD = st.secrets["gmail_password"]
MAILBOX = 'inbox'

REMITENTE_VALIDO = 'alertas@davibank.cr'
FRASE_CLAVE = 'davibank le notifica que la transacción realizada'

# ================= FUNCIONES AUX =================
def normalize_number_text(s):
    s = s.strip().replace(',', '')
    return s

def asignar_categoria(texto, categorias):
    texto = str(texto).lower()
    for cat, keywords in categorias.items():
        if any(k.lower() in texto for k in keywords):
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

    from_email = email.utils.parseaddr(msg['From'])[1].lower()
    if from_email != REMITENTE_VALIDO:
        continue

    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                body += part.get_payload(decode=True).decode(errors='ignore')
    else:
        body = msg.get_payload(decode=True).decode(errors='ignore')

    body_lower = body.lower()
    if FRASE_CLAVE not in body_lower or 'fue aprobada' not in body_lower:
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

    if 0 < monto < 10000000:
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
    'Supermercado': ['super', 'market', 'mas x menos', 'fresh market'],
    'Restaurante': ['didi', 'burger', 'restaurant', 'food', 'cafe'],
    'Gasolina': ['estacion de servicio'],
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

# ================= GRÁFICOS =================
chart = alt.Chart(sum_categoria_mensual).mark_bar().encode(
    x=alt.X('categoria:N', title='Categoría'),
    y=alt.Y('monto:Q', title='Monto'),
    color='moneda:N',
    column='mes:N'
)
st.altair_chart(chart, use_container_width=True)

ultimo_mes = sum_categoria_mensual['mes'].max()
df_ultimo_mes = sum_categoria_mensual[sum_categoria_mensual['mes'] == ultimo_mes]

for moneda in ['CRC','USD']:
    df_moneda = df_ultimo_mes[df_ultimo_mes['moneda'] == moneda]
    if not df_moneda.empty:
        st.subheader(f"Gastos por categoría en {moneda} - último mes")
        fig, ax = plt.subplots(figsize=(5,5))
        ax.pie(df_moneda['monto'], labels=df_moneda['categoria'], autopct='%1.1f%%')
        st.pyplot(fig)

# ================= DÍA MAYOR GASTO =================
mayor_dia_crc = sum_diaria['CRC'].idxmax() if 'CRC' in sum_diaria.columns else None
mayor_dia_usd = sum_diaria['USD'].idxmax() if 'USD' in sum_diaria.columns else None

st.subheader("📈 Día con mayor gasto por moneda")
if mayor_dia_crc:
    st.write(f"Mayor gasto en CRC: ₡{sum_diaria.loc[mayor_dia_crc,'CRC']:,.2f} el día {mayor_dia_crc.date()}")
if mayor_dia_usd:
    st.write(f"Mayor gasto en USD: ${sum_diaria.loc[mayor_dia_usd,'USD']:,.2f} el día {mayor_dia_usd.date()}")

