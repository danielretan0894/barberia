from base_datos import GestorBaseDatos
from werkzeug.security import generate_password_hash

db = GestorBaseDatos()
conexion = db.conectar()
cursor = conexion.cursor()

# Creamos el usuario superadmin con contraseña '12345'
pass_hash = generate_password_hash('12345')
cursor.execute("INSERT OR REPLACE INTO usuarios (id_negocio, usuario, password, rol, cambiar_password) VALUES (1, 'supermaster', ?, 'superadmin', 0)", (pass_hash,))

conexion.commit()
conexion.close()
print("¡Cuenta de superadmin creada con éxito!")