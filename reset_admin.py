import sqlite3
from werkzeug.security import generate_password_hash

def arreglar_password_definitivo():
    # Conectamos a la base de datos correcta
    conexion = sqlite3.connect('barberia_saas.db')
    cursor = conexion.cursor()
    
    # Generamos el hash seguro para la contraseña "12345"
    password_segura = generate_password_hash("12345")
    
    # Actualizamos directamente en la tabla 'usuarios' donde el rol sea superadmin o el usuario sea admin/master
    cursor.execute("""
        UPDATE usuarios 
        SET password = ? 
        WHERE rol = 'superadmin' OR usuario = 'superadmin' OR usuario = 'admin'
    """, (password_segura,))
    
    # Si no encontró ninguno por rol/nombre, por seguridad actualiza el primer usuario de la lista
    if cursor.rowcount == 0:
        cursor.execute("UPDATE usuarios SET password = ? WHERE id = 1", (password_segura,))
    
    conexion.commit()
    conexion.close()
    
    print("¡LISTO! La contraseña ha sido actualizada a: 12345")

if __name__ == '__main__':
    arreglar_password_definitivo()