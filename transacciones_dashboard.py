import streamlit as st
import imaplib
import email
import re
from bs4 import BeautifulSoup
from datetime import datetime, date
import pandas as pd

# ===============================
# CONFIGURACIÓN INICIAL STREAMLIT
# ===============================
st.set_page_config(page_title="Transacciones Scotia", layout="wide")

st.title("📩 Lectura segura de correos de compras Scotia")
st.caption("Lee y filtra automáticamente las transacciones del mes actual desde tu bandeja de entrada.")

# ===============================
# FUNCIÓN AUXILIAR
# ===============================
def normalize_number_text(text):
    """
    Normaliza valores numéricos con comas/puntos según formato latino.
    """
    text = text.replace(",", ".")
    text = re.sub(r"[^\d.]", "", text)
    return text

# ===============================
# BLOQUE IMAP SEGURIDAD Y FILTROS
# ===============================
IMAP_HOST = 'imap.gmail.com'
USUARIO = 'jjtransacciones@gmail.com'
PASSWORD = st.secrets["gmail_password"]  # ⚠️ Guarda la clave en .streamlit/secrets.toml
MAILBOX = 'inbox'

try:
    mail = imaplib.IMAP4_SSL(IMAP_HOST)
    mail.login(USUARIO, PASSWORD)
    mail.select(MAILBOX)
except Exception as e:
    st.error(f"❌ No se pudo conectar al servidor IMAP: {e}")
    st.stop()

# 🔹 Lee solo mensajes recientes (últimos 30) y filtra remitentes legítimos
status, mensajes = mail.search(None, '(FROM "scotiabank" SUBJECT "Compra")')
if status != "OK":
    st.error("No se pudieron obtener mensajes del servidor IMAP.")
    mail.logout()
    st.stop()

mensajes_ids = mensajes[0].split()[-30:]  # solo los más recientes
data = []

hoy = date.today()
mes_actual = hoy.month
anio_actual = hoy.year

for num in mensajes_ids:
    status, msg_data = mail.fetch(num, '(RFC822)')
    if status != "OK":
        continue

    msg = email.message_from_bytes(msg_data[0][1])
    from_ = msg.get('From', '').lower()
    subject = msg.get('Subject', '')

    # 🔸 Filtra remitentes o temas no deseados
    if not any(k in from_ for k in ["scotiabank", "banco"]):
        continue

    # 🔸 Obtiene fecha segura
    try:
        fecha_correo = email.utils.parsedate_to_datetime(msg['Date']).date()
    except Exception:
        fecha_correo = hoy

    # --- EXTRAER CUERPO DEL MENSAJE ---
    body = ""
    for part in msg.walk():
        content_type = part.get_content_type()
        if content_type == "text/plain":
            body += part.get_payload(decode=True).decode(errors='ignore')
        elif content_type == "text/html":
            html = part.get_payload(decode=True).decode(errors='ignore')
            # Limpia HTML y elimina etiquetas
            body += BeautifulSoup(html, "html.parser").get_text(separator=" ")

    # --- FILTRO ANTISPAM ---
    if any(x in body.lower() for x in ["promoción", "válido", "sorteo", "ganador", "campaña"]):
        continue

    # --- BUSCAR MONTOS ---
    currency_pat = re.compile(r'(?P<cur>CRC|₡|USD|\$)\s*(?P<val>\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)', re.IGNORECASE)
    decimal_pat = re.compile(r'(?P<val>\d{1,3}(?:[.,]\d{3})*[.,]\d{2})')

    for line in body.splitlines():
        line = line.strip()
        if not line:
            continue

        # Extraer fecha de transacción del texto
        fecha_match = re.search(r'(\d{2}/\d{2}/\d{4})', line)
        fecha_linea = datetime.strptime(fecha_match.group(1), '%d/%m/%Y').date() if fecha_match else fecha_correo

        # Solo procesa transacciones del mes actual
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

# ===============================
# CREAR DATAFRAME Y VISUALIZACIÓN
# ===============================
if not data:
    st.warning("⚠️ No se encontraron transacciones válidas este mes.")
    st.stop()

df = pd.DataFrame(data)
df = df.sort_values(by="fecha", ascending=False)

# Mostrar tabla
st.dataframe(df, use_container_width=True)

# Estadísticas básicas
st.divider()
st.subheader("📊 Resumen del mes actual")

col1, col2 = st.columns(2)
with col1:
    total_crc = df.loc[df['moneda'] == 'CRC', 'monto'].sum()
    st.metric("Total CRC", f"₡{total_crc:,.2f}")

with col2:
    total_usd = df.loc[df['moneda'] == 'USD', 'monto'].sum()
    st.metric("Total USD", f"${total_usd:,.2f}")

st.success("✅ Lectura completada correctamente")
