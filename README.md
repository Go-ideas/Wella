# Wella — Decision Simulator

Streamlit app diseñada para desplegarse **sin datos del estudio**. El cliente carga un archivo cifrado `.goideas` en cada sesión y proporciona la clave por separado.

## Arquitectura de confidencialidad

- GitHub contiene sólo código. No incluye `.db`, `.sav`, `.xlsx`, `.csv` ni `.goideas`.
- El reporteador **no acepta bases en claro** desde la interfaz.
- El archivo `.goideas` usa AES-256-GCM con una clave derivada mediante scrypt.
- La base SQLite se descifra en RAM y se abre con `sqlite3.Connection.deserialize()`; no se escribe una copia descifrada a disco.
- El DataFrame analítico permanece sólo en `st.session_state` durante la sesión.
- El botón **Cerrar sesión y borrar datos de memoria** elimina dataset y metadatos de la sesión.
- No se usa `st.cache_data` para datos del cliente.

> Nota: en Streamlit Community Cloud el archivo cifrado y la clave llegan al backend de Streamlit durante la sesión. Para requisitos de confidencialidad superiores, desplegar el mismo código en infraestructura privada del cliente/Go Ideas.

## Despliegue en Streamlit Community Cloud

1. Conectar GitHub a Streamlit Community Cloud.
2. Elegir este repositorio/branch.
3. Main file path: `app.py`.
4. Python compatible con las dependencias de `requirements.txt`.
5. No agregar datos ni claves en Secrets; este proyecto no las necesita.

## Generar el archivo cifrado

La base analítica `.db` se genera internamente y después se cifra:

```bash
python tools/encrypt_database.py Wella_Analitica.db Wella_Coloracion.goideas
```

Entregar el archivo `.goideas` y la clave por **canales separados**.

## Ejecución local

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Vistas

- Resumen ejecutivo
- Árbol dinámico D1 → D2 → D3
- Drivers MaxDiff
- Simulador de sustitución
- Simulador de anaquel
