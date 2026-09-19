import sqlite3
from werkzeug.security import generate_password_hash

# Conectamos a la base de datos
conexion = sqlite3.connect("barberia.db")
cursor = conexion.cursor()

# Creamos la contraseña encriptada para '12345'
pass_hash = generate_password_hash("12345")

# Borramos cualquier registro previo de supermaster para evitar duplicados
cursor.execute("DELETE FROM usuarios WHERE usuario = 'supermaster'")

# Insertamos el superadministrador global con id_negocio NULL
cursor.execute(
    """
    INSERT INTO usuarios (id_negocio, usuario, password, rol, cambiar_password) 
    VALUES (NULL, 'supermaster', ?, 'superadmin', 0)
""",
    (pass_hash,),
)

conexion.commit()

# Verificamos e imprimimos todos los usuarios actuales en la base de datos
print("\n=== LISTA ACTUALIZADA DE USUARIOS EN LA BASE DE DATOS ===")
cursor.execute("SELECT id, id_negocio, usuario, rol FROM usuarios")
for u in cursor.fetchall():
    print(f"ID: {u[0]} | Negocio ID: {u[1]} | Usuario: {u[2]} | Rol: {u[3]}")
print("=========================================================\n")

conexion.close()
print("¡Listo! El usuario 'supermaster' con contraseña '12345' ha sido forzado.")