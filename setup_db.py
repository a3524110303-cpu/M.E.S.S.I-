import mysql.connector
import sys

try:
    conn = mysql.connector.connect(
        host="127.0.0.1",
        user="root",
        password="goku123"
    )
    cursor = conn.cursor()
    print("Conexión a MySQL exitosa.")
    
    # Create DB
    cursor.execute("CREATE DATABASE IF NOT EXISTS messi CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
    print("Base de datos 'messi' asegurada.")
    
    # Create User
    try:
        cursor.execute("CREATE USER 'messi'@'127.0.0.1' IDENTIFIED BY 'messipassword';")
        print("Usuario 'messi' creado.")
    except mysql.connector.Error as err:
        if err.errno == 1396: # Operation CREATE USER failed (already exists)
            print("El usuario 'messi' ya existe. Modificando contraseña por seguridad...")
            cursor.execute("ALTER USER 'messi'@'127.0.0.1' IDENTIFIED BY 'messipassword';")
        else:
            raise

    # Grant application permissions
    cursor.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON messi.* TO 'messi'@'127.0.0.1';")
    
    # Grant temp permissions for initialization
    cursor.execute("GRANT CREATE, INDEX, REFERENCES ON messi.* TO 'messi'@'127.0.0.1';")
    
    cursor.execute("FLUSH PRIVILEGES;")
    print("Permisos concedidos.")
    
    cursor.close()
    conn.close()
except Exception as e:
    print("Error:", e)
    sys.exit(1)
