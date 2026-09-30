# Seguridad y confidencialidad

## Modelo de datos

El repositorio y la aplicación desplegada no contienen observaciones del estudio. La única fuente de datos es el archivo cifrado que el usuario selecciona en su navegador durante la sesión.

## Cifrado del paquete

Formato propietario simple `GIDEAS01`:

- AES-256-GCM para confidencialidad e integridad.
- scrypt para derivación de clave desde contraseña.
- Salt aleatorio de 16 bytes.
- Nonce aleatorio de 12 bytes.
- Compresión previa al cifrado.
- AAD fija para evitar reutilización accidental del formato en otro contexto.

## Servidor

La aplicación descifra únicamente en RAM. No crea archivos temporales con la base en claro. El código falla de forma segura si el runtime no soporta `sqlite3.Connection.deserialize()`.

## Operación recomendada

1. Go Ideas genera la base analítica minimizada.
2. Go Ideas cifra localmente a `.goideas .
3. El archivo y la clave se envían por canales separados.
4. Cliente abre el sitio y carga el archivo.
5. Cliente introduce la clave.
6. Al terminar, usa “Cerrar sesión y borrar datos de memoria” y cierra la pestaña.

## Límites

Community Cloud sigue siendo infraestructura de terceros: el paquete cifrado y la clave son procesados por el backend durante la sesión. Si el acuerdo del cliente prohíbe procesamiento en nube pública, desplegar localmente o en infraestructura privada.
