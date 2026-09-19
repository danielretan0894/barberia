import sqlite3
from werkzeug.security import generate_password_hash

# Conectamos a la base de datos local
conexion = sqlite3.connect("barberia.db")
cursor = conexion.cursor()

# Nos aseguramos de que exista la tabla usuarios (por si acaso)
cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_negocio INTEGER,
        usuario TEXT,
        password TEXT,
        rol TEXT,
        cambiar_password INTEGER DEFAULT 0
    )
"""
)

# Generamos el hash seguro de la contraseña '12345'
pass_hash = generate_password_hash("12345")

# Eliminamos cualquier usuario supermaster anterior duplicado o mal configurado
cursor.execute("DELETE FROM usuarios WHERE usuario = 'supermaster'")

# Insertamos el superadministrador global (id_negocio = NULL para que sea el dueño de todo el SaaS)
cursor.execute(
    """
    INSERT INTO usuarios (id_negocio, usuario, password, rol, cambiar_password) 
    VALUES (NULL, 'supermaster', ?, 'superadmin', 0)
""",
    (pass_hash,),
)

conexion.commit()
conexion.close()

print(
    "¡Cuenta de superadmin creada con éxito! Ya puedes iniciar sesión con 'supermaster' y '12345'."
)