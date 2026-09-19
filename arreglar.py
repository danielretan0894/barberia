import sqlite3

conexion = sqlite3.connect("barberia.db")
cursor = conexion.cursor()

# Creamos la tabla transacciones asegurando que tenga la columna categoria
cursor.execute("""
    CREATE TABLE IF NOT EXISTS transacciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_negocio INTEGER,
        tipo TEXT,
        monto REAL,
        descripcion TEXT,
        metodo_pago TEXT,
        categoria TEXT DEFAULT 'General',
        fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")

conexion.commit()
conexion.close()
print("¡Base de datos creada y actualizada con éxito!")