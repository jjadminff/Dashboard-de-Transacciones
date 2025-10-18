💳 Dashboard de Transacciones de Tarjeta de Crédito

<img width="92" height="20" alt="image" src="https://github.com/user-attachments/assets/a9f2ac94-e32d-49b1-bf83-9d2fb6e62889" /> 
<img width="130" height="20" alt="image" src="https://github.com/user-attachments/assets/52bb8d2d-a4df-41fa-9ad0-c94909c7b928" />



Este proyecto permite extraer automáticamente las transacciones bancarias desde tu cuenta de correo electrónico (Hotmail o Gmail) y visualizarlas en un dashboard interactivo desarrollado con Streamlit.

El sistema soporta montos en Colones (CRC) y Dólares (USD), categorización automática de gastos, y reportes diarios y mensuales.

📝 Características

🔗 Conexión IMAP a cuentas de correo Hotmail o Gmail.

📬 Extracción automática de montos y fechas directamente desde el cuerpo de los correos.

💰 Soporte para múltiples monedas: CRC y USD.

📆 Filtrado automático de transacciones del mes en curso.

🏷 Categorías personalizables (Amazon, Supermercado, Restaurante, etc.).

📊 Dashboard interactivo con:

Tabla detallada de transacciones.

Suma diaria y mensual por moneda.

Resumen mensual por categoría y moneda.

Gráficos de barras y pastel interactivos.

Identificación del día con mayor gasto por moneda.

🛠 Tecnologías usadas

Python 3.10+

pandas
 – manejo y análisis de datos.

Streamlit
 – interfaz web interactiva.

matplotlib
 – gráficos de pastel.

Altair
 – gráficos de barras interactivos.

imaplib y email – conexión y lectura de correos vía IMAP.

re – expresiones regulares para extracción de montos y fechas.

⚡ Instalación

Clona el repositorio:

git clone https://github.com/tu_usuario/transacciones-dashboard.git
cd transacciones-dashboard


Crea un entorno virtual e instala dependencias:

python -m venv venv
# Linux / Mac
source venv/bin/activate
# Windows
venv\Scripts\activate

pip install -r requirements.txt


Archivo requirements.txt recomendado:

pandas==2.0.3
streamlit==1.30.0
matplotlib==3.8.0
altair==5.0.1
openpyxl==3.1.2
numpy==1.26.2

⚙️ Configuración

Edita tus credenciales y ajustes en el archivo principal del proyecto:

IMAP_HOST = 'imap.gmail.com'
USUARIO = 'tu_correo@gmail.com'
PASSWORD = 'tu_contraseña_o_contraseña_de_aplicación'
MAILBOX = 'inbox'

Opcional: Personaliza tus categorías

Puedes definir palabras clave para agrupar transacciones automáticamente según la descripción (ejemplo: “Amazon”, “Supermercado”, “Restaurante”, etc.).

▶️ Uso

Ejecuta el dashboard localmente con:

streamlit run transacciones_dashboard.py


El dashboard se abrirá automáticamente en tu navegador predeterminado.

📅 Solo se mostrarán las transacciones del mes en curso.
💵 Los montos se separan por moneda y se pueden visualizar por categoría.

🔄 Flujo de trabajo

Llegan los correos de transacciones a tu bandeja de entrada.

El script se conecta vía IMAP y analiza los correos del mes actual.

Se extraen los montos, fechas y descripciones de cada transacción.

Cada transacción se clasifica en una categoría.

El dashboard genera tablas y gráficos para un análisis rápido.

🔒 Consideraciones de seguridad

Si tu correo tiene autenticación en dos pasos (2FA), usa una contraseña de aplicación.

Nunca compartas tu contraseña directamente.

Puedes crear un archivo .env para almacenar usuario y contraseña de forma segura.

Ejemplo de .env:

EMAIL_USER=tu_correo@gmail.com
EMAIL_PASS=tu_contraseña_segura

🤝 Contribuciones

¡Las contribuciones son bienvenidas!
Puedes abrir un issue o enviar un pull request si deseas agregar nuevas funciones como:

Selector de mes para visualizar periodos anteriores.

Exportación de reportes a Excel o PDF.

Alertas automáticas por correo o notificaciones de gasto.

📄 Licencia

Este proyecto está bajo la MIT License, lo que permite su uso, modificación y distribución libre con fines personales o académicos.
