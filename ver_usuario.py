from base_datos import GestorBaseDatos

db = GestorBaseDatos()
conexion = db.conectar()
cursor = conexion.cursor()

cursor.execute("SELECT u.id, n.nombre_barberia, u.usuario, u.rol FROM usuarios u JOIN negocios n ON u.id_negocio = n.id")
usuarios = cursor.fetchall()

print("\n--- LISTA DE USUARIOS REGISTRADOS ---")
for u in usuarios:
    print(f"Negocio: {u[1]} | Usuario: {u[2]} | Rol: {u[3]}")
print("--------------------------------------\n")

conexion.close()