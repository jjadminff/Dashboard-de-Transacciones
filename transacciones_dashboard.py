import imaplib
import email
import re
import pandas as pd
from datetime import datetime, date
import streamlit as st
import matplotlib.pyplot as plt
import altair as alt

# CONFIGURACIÓN
IMAP_HOST = 'imap.gmail.com'
USUARIO = 'jjtransacciones@gmail.com'
PASSWORD = 'joblzeglxxprjzqr'
MAILBOX = 'inbox'

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

for num in mensajes[0].split():
    status, msg_data = mail.fetch(num, '(RFC822)')
    msg = email.message_from_bytes(msg_data[0][1])
    fecha_correo = email.utils.parsedate_to_datetime(msg['Date']).date()

    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                body += part.get_payload(decode=True).decode(errors='ignore')
    else:
        body = msg.get_payload(decode=True).decode(errors='ignore')

    currency_pat = re.compile(r'(?P<cur>CRC|₡|USD|\$)\s*(?P<val>\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)', re.IGNORECASE)
    decimal_pat = re.compile(r'(?P<val>\d{1,3}(?:[.,]\d{3})*[.,]\d{2})')

    for line in body.splitlines():
        line = line.strip()
        if not line:
            continue

        # Extraer fecha de transacción del texto
        fecha_match = re.search(r'(\d{2}/\d{2}/\d{4})', line)
        fecha_linea = datetime.strptime(fecha_match.group(1), '%d/%m/%Y').date() if fecha_match else fecha_correo

        # --- FILTRO: solo mes en curso ---
        if fecha_linea.month != mes_actual or fecha_linea.year != anio_actual:
            continue

        matched_any = False
        for m in currency_pat.finditer(line):
            matched_any = True
            moneda_raw = m.group('cur') or ''
            valor_raw = m.group('val')
            limpio = normalize_number_text(valor_raw)
            try:
                monto = float(limpio)
            except:
                continue
            tipo_moneda = 'USD' if moneda_raw.strip().upper() in ['USD', '$'] else 'CRC'
            if 0 < monto < 10000000:
                data.append({'fecha': fecha_linea, 'monto': monto, 'moneda': tipo_moneda, 'detalle': line})

        if not matched_any:
            for m in decimal_pat.finditer(line):
                valor_raw = m.group('val')
                limpio = normalize_number_text(valor_raw)
                try:
                    monto = float(limpio)
                except:
                    continue
                tipo_moneda = 'CRC'
                if 0 < monto < 10000000:
                    data.append({'fecha': fecha_linea, 'monto': monto, 'moneda': tipo_moneda, 'detalle': line})

mail.logout()

# --- CREAR DATAFRAME ---
df = pd.DataFrame(data)
if df.empty:
    st.warning("No se encontraron montos válidos en el mes en curso.")
else:
    st.subheader("Detalle de transacciones")
    st.dataframe(df[['fecha','monto','moneda','detalle']])

df['fecha'] = pd.to_datetime(df['fecha'])
df['mes'] = df['fecha'].dt.to_period('M').astype(str)

# --- CATEGORÍAS ---
categorias = {
    'Amazon': ['amazon', 'prime'],
    'Pricesmart': ['Pricesmart Costa Rica'],
    'Supermercado': ['mega super', 'mas x menos', 'super belen heredia','fresh market', 'sabana de oro'],
    'Restaurante': ['didi', 'burger', 'restaurant', 'cafe'],
    'Otros': []
}
df['categoria'] = df['detalle'].apply(lambda x: asignar_categoria(x, categorias))

# --- RESÚMENES ---
sum_diaria = df.groupby(['fecha','moneda'])['monto'].sum().unstack(fill_value=0)
sum_mensual = df.groupby(['mes','moneda'])['monto'].sum().unstack(fill_value=0)
sum_categoria_mensual = df.groupby(['mes','categoria','moneda'])['monto'].sum().reset_index()

# --- DASHBOARD ---
st.title("💳 Transacciones Tarjeta de Credito JJ")

st.subheader("Suma diaria total (por moneda)")
st.dataframe(sum_diaria)

st.subheader("Suma mensual total (por moneda)")
st.dataframe(sum_mensual)

st.subheader("Resumen mensual por categoría (por moneda)")
st.dataframe(sum_categoria_mensual)

# --- GRÁFICO BARRAS AGRUPADAS POR MONEDA ---
chart = alt.Chart(sum_categoria_mensual).mark_bar().encode(
    x=alt.X('categoria:N', title='Categoría'),
    y=alt.Y('monto:Q', title='Monto'),
    color='moneda:N',
    column='mes:N'  # columnas por mes
)
st.altair_chart(chart, use_container_width=True)

# --- GRÁFICO PIE DEL ÚLTIMO MES ---
ultimo_mes = sum_categoria_mensual['mes'].max()
df_ultimo_mes = sum_categoria_mensual[sum_categoria_mensual['mes'] == ultimo_mes]
for moneda in ['CRC','USD']:
    df_moneda = df_ultimo_mes[df_ultimo_mes['moneda'] == moneda]
    if not df_moneda.empty:
        st.subheader(f"Gastos por categoría en {moneda} - último mes")
        fig, ax = plt.subplots(figsize=(5,5))
        ax.pie(df_moneda['monto'], labels=df_moneda['categoria'], autopct='%1.1f%%')
        st.pyplot(fig)

# --- DÍA CON MAYOR GASTO POR MONEDA ---
mayor_dia_crc = sum_diaria['CRC'].idxmax() if 'CRC' in sum_diaria.columns else None
mayor_dia_usd = sum_diaria['USD'].idxmax() if 'USD' in sum_diaria.columns else None

total_crc = sum_diaria.loc[mayor_dia_crc, 'CRC'] if mayor_dia_crc else 0
total_usd = sum_diaria.loc[mayor_dia_usd, 'USD'] if mayor_dia_usd else 0

st.subheader("📈 Día con mayor gasto por moneda")
if mayor_dia_crc:
    st.write(f"Mayor gasto en CRC: {total_crc:,.2f} ₡ el día {mayor_dia_crc.date()}")
if mayor_dia_usd:
    st.write(f"Mayor gasto en USD: ${total_usd:,.2f} el día {mayor_dia_usd.date()}")

