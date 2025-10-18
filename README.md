# 💳 Dashboard de Transacciones de Tarjeta de Crédito

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-orange.svg)

Este proyecto permite extraer automáticamente las transacciones de tu cuenta de correo electrónico (Hotmail/Gmail) y visualizarlas en un **dashboard interactivo** usando **Streamlit**. Soporta montos en **Colones (CRC)** y **Dólares (USD)**, clasificación por categorías y reportes diarios y mensuales.

## 📝 Características

- Conexión vía IMAP a cuentas de correo (Hotmail/Gmail).  
- Extracción de montos de transacciones directamente desde el cuerpo de los correos.  
- Soporte para múltiples monedas: CRC y USD.  
- Filtrado automático de transacciones por mes en curso.  
- Categorías personalizables para clasificar gastos (Amazon, Supermercado, Restaurante, etc.).  
- Dashboard interactivo con:
  - Tabla de detalle de transacciones.
  - Suma diaria total por moneda.
  - Suma mensual total por moneda.
  - Resumen mensual por categoría y moneda.
  - Gráfico de barras agrupadas por categoría y moneda.
  - Gráfico de pastel por categoría para el último mes.
  - Identificación del día con mayor gasto por moneda.

## 🛠 Tecnologías usadas

- Python 3.10+
- [pandas](https://pandas.pydata.org/) – manejo y análisis de datos.
- [Streamlit](https://streamlit.io/) – interfaz web interactiva.
- [matplotlib](https://matplotlib.org/) – gráficos de pastel.
- [Altair](https://altair-viz.github.io/) – gráficos de barras interactivos.
- `imaplib` y `email` – conexión y lectura de correos vía IMAP.
- `re` – expresiones regulares para extracción de montos y fechas.

## ⚡ Instalación

1. Clonar el repositorio:

```bash
git clone https://github.com/tu_usuario/transacciones-dashboard.git
cd transacciones-dashboard
Crear un entorno virtual e instalar dependencias:

bash
Copy code
python -m venv venv
# Linux/Mac
source venv/bin/activate
# Windows
venv\Scripts\activate

pip install -r requirements.txt
Archivo requirements.txt sugerido:

nginx
Copy code
pandas
streamlit
matplotlib
altair
⚙️ Configuración
Editar el archivo transacciones_dashboard.py con tus datos:

python
Copy code
IMAP_HOST = 'imap.gmail.com'
USUARIO = 'tu_correo@gmail.com'
PASSWORD = 'tu_contraseña_o_contraseña_de_aplicación'
MAILBOX = 'inbox'
Opcional: personalizar las categorías:

python
Copy code
categorias = {
    'Amazon': ['amazon', 'prime'],
    'Pricesmart': ['Pricesmart Costa Rica'],
    'Supermercado': ['mega super', 'mas x menos', 'super belen heredia', 'sabana de oro'],
    'Restaurante': ['didi', 'burger', 'restaurant', 'cafe'],
    'Otros': []
}
▶️ Uso
Ejecutar el dashboard con Streamlit:

bash
Copy code
streamlit run transacciones_dashboard.py
El dashboard se abrirá en tu navegador web predeterminado.

Solo se mostrarán las transacciones del mes en curso.

Los montos se separan por moneda y se pueden visualizar por categoría.

🔄 Flujo de trabajo
Llegan los correos de transacciones a tu bandeja.

El script conecta vía IMAP y lee los correos del mes actual.

Extrae montos y fechas de las transacciones.

Clasifica cada transacción en una categoría.

Genera tablas y gráficos interactivos para análisis rápido.

🔒 Consideraciones de seguridad
Se recomienda usar contraseñas de aplicación si tu correo tiene 2FA activado.

Nunca compartas tu contraseña directamente.

Puedes configurar un archivo .env para almacenar usuario y contraseña de manera segura.

🤝 Contribuciones
¡Bienvenidas! Puedes abrir un issue o enviar un pull request si quieres agregar funcionalidades como:

Selector de mes para ver meses anteriores.

Exportación de reportes a Excel o PDF.

Alertas automáticas de gasto diario o mensual.

📄 Licencia
MIT License – libre para uso personal y académico.
