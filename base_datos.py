import sqlite3
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash

class GestorBaseDatos:
    def __init__(self, nombre_bd="barberia.db"):
        self.nombre_bd = nombre_bd
        self.inicializar_tablas()

    def conectar(self):
        return sqlite3.connect(self.nombre_bd)

    def inicializar_tablas(self):
        conexion = self.conectar()
        cursor = conexion.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS negocios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre_barberia TEXT,
                dias_restantes INTEGER DEFAULT 27,
                precio_mensual REAL DEFAULT 500.0
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ingresos_saas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_negocio INTEGER,
                monto REAL,
                descripcion TEXT,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(id_negocio) REFERENCES negocios(id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_negocio INTEGER,
                usuario TEXT,
                password TEXT,
                rol TEXT,
                cambiar_password INTEGER DEFAULT 0,
                FOREIGN KEY(id_negocio) REFERENCES negocios(id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS barberos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_negocio INTEGER,
                nombre TEXT,
                comision REAL,
                FOREIGN KEY(id_negocio) REFERENCES negocios(id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS servicios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_negocio INTEGER,
                nombre TEXT,
                precio REAL,
                tipo TEXT,
                stock INTEGER DEFAULT 0,
                stock_minimo INTEGER DEFAULT 5,
                FOREIGN KEY(id_negocio) REFERENCES negocios(id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transacciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_negocio INTEGER,
                tipo TEXT,
                monto REAL,
                descripcion TEXT,
                metodo_pago TEXT,
                categoria TEXT DEFAULT 'General',
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(id_negocio) REFERENCES negocios(id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agenda (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_negocio INTEGER,
                fecha_cita TEXT,
                hora TEXT,
                cliente TEXT,
                telefono TEXT,
                barbero TEXT,
                estado TEXT DEFAULT 'Agendada',
                FOREIGN KEY(id_negocio) REFERENCES negocios(id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_negocio INTEGER,
                nombre TEXT,
                telefono TEXT,
                puntos INTEGER DEFAULT 0,
                notas TEXT,
                FOREIGN KEY(id_negocio) REFERENCES negocios(id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cupones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_negocio INTEGER,
                codigo TEXT,
                tipo TEXT,
                valor REAL,
                FOREIGN KEY(id_negocio) REFERENCES negocios(id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS config_puntos (
                id_negocio INTEGER PRIMARY KEY,
                puntos_meta INTEGER DEFAULT 100,
                FOREIGN KEY(id_negocio) REFERENCES negocios(id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cierres_caja (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_negocio INTEGER,
                fondo_inicial REAL,
                efectivo_teorico REAL,
                efectivo_real REAL,
                diferencia REAL,
                notas TEXT,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(id_negocio) REFERENCES negocios(id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS caja_diaria (
                id_negocio INTEGER PRIMARY KEY,
                monto_inicial REAL,
                fecha_apertura TEXT
            )
        ''')

        conexion.commit()
        conexion.close()
        self.asegurar_cuenta_demo()
        self.asegurar_superadmin_global()

    def verificar_caja_abierta_hoy(self, id_negocio):
        hoy = str(date.today())
        conexion = self.conectar()
        cursor = conexion.cursor()
        cursor.execute("SELECT monto_inicial FROM caja_diaria WHERE id_negocio = ? AND fecha_apertura = ?", (id_negocio, hoy))
        res = cursor.fetchone()
        conexion.close()
        return res[0] if res else None

    def abrir_caja_hoy(self, id_negocio, monto):
        hoy = str(date.today())
        conexion = self.conectar()
        cursor = conexion.cursor()
        cursor.execute("INSERT OR REPLACE INTO caja_diaria (id_negocio, monto_inicial, fecha_apertura) VALUES (?, ?, ?)", (id_negocio, monto, hoy))
        
        if monto > 0:
            cursor.execute("INSERT INTO transacciones (id_negocio, tipo, monto, descripcion, metodo_pago, categoria) VALUES (?, 'ingreso', ?, ?, 'Efectivo', 'Apertura de Caja')",
                           (id_negocio, monto, f"Fondo inicial de caja del día {hoy}"))

        conexion.commit()
        conexion.close()

    def cerrar_caja_hoy(self, id_negocio):
        conexion = self.conectar()
        cursor = conexion.cursor()
        cursor.execute("DELETE FROM caja_diaria WHERE id_negocio = ?", (id_negocio,))
        conexion.commit()
        conexion.close()

    def reiniciar_cuenta_demo(self):
        conexion = self.conectar()
        cursor = conexion.cursor()
        cursor.execute("DELETE FROM transacciones WHERE id_negocio = 1")
        cursor.execute("DELETE FROM agenda WHERE id_negocio = 1")
        cursor.execute("DELETE FROM clientes WHERE id_negocio = 1")
        cursor.execute("DELETE FROM cierres_caja WHERE id_negocio = 1")
        cursor.execute("DELETE FROM caja_diaria WHERE id_negocio = 1")
        cursor.execute("UPDATE servicios SET stock = 15 WHERE id_negocio = 1 AND tipo = 'producto'")
        conexion.commit()
        conexion.close()

    def asegurar_cuenta_demo(self):
        conexion = self.conectar()
        cursor = conexion.cursor()
        cursor.execute("SELECT id FROM negocios WHERE id = 1")
        if not cursor.fetchone():
            cursor.execute("INSERT INTO negocios (id, nombre_barberia, dias_restantes, precio_mensual) VALUES (1, 'Demo Barber', 27, 500.0)")
            pass_hash = generate_password_hash('12345')
            cursor.execute("INSERT INTO usuarios (id_negocio, usuario, password, rol, cambiar_password) VALUES (1, 'demo', ?, 'admin', 1)", (pass_hash,))
            cursor.execute("INSERT INTO barberos (id_negocio, nombre, comision) VALUES (1, 'Carlos Estilista', 50)")
            cursor.execute("INSERT INTO servicios (id_negocio, nombre, precio, tipo, stock, stock_minimo) VALUES (1, 'Corte Clásico', 150.0, 'servicio', 0, 5)")
            cursor.execute("INSERT INTO servicios (id_negocio, nombre, precio, tipo, stock, stock_minimo) VALUES (1, 'Cera Mate', 200.0, 'producto', 15, 3)")
            cursor.execute("INSERT INTO cupones (id_negocio, codigo, tipo, valor) VALUES (1, 'BARBER10', 'porcentaje', 10)")
            cursor.execute("INSERT OR IGNORE INTO config_puntos (id_negocio, puntos_meta) VALUES (1, 100)")
            conexion.commit()
        else:
            self.reiniciar_cuenta_demo()
        conexion.close()

    def asegurar_superadmin_global(self):
        conexion = self.conectar()
        cursor = conexion.cursor()
        cursor.execute("SELECT id FROM usuarios WHERE usuario = 'supermaster'")
        if not cursor.fetchone():
            pass_hash = generate_password_hash('12345')
            cursor.execute("INSERT INTO usuarios (id_negocio, usuario, password, rol, cambiar_password) VALUES (NULL, 'supermaster', ?, 'superadmin', 0)", (pass_hash,))
            conexion.commit()
        conexion.close()

    def verificar_usuario_multiples_negocios(self, usuario, password):
        conexion = self.conectar()
        cursor = conexion.cursor()
        cursor.execute("""
            SELECT u.rol, n.id, n.nombre_barberia, u.password, u.cambiar_password 
            FROM usuarios u 
            LEFT JOIN negocios n ON u.id_negocio = n.id 
            WHERE u.usuario = ?
        """, (usuario,))
        resultados = cursor.fetchall()
        conexion.close()
        
        validos = []
        for rol, id_negocio, nombre_barberia, pass_db, cambiar_pass in resultados:
            if check_password_hash(pass_db, password):
                validos.append((rol, id_negocio or 0, nombre_barberia or 'Panel Global SaaS', cambiar_pass))
        return validos

    def obtener_resumen(self, id_negocio):
        conexion = self.conectar()
        cursor = conexion.cursor()
        
        cursor.execute("SELECT SUM(monto) FROM transacciones WHERE id_negocio = ? AND tipo = 'ingreso' AND categoria NOT IN ('Cierre de Caja', 'Apertura de Caja')", (id_negocio,))
        ingresos = cursor.fetchone()[0] or 0.0
        
        cursor.execute("SELECT SUM(monto) FROM transacciones WHERE id_negocio = ? AND tipo = 'gasto'", (id_negocio,))
        gastos = cursor.fetchone()[0] or 0.0
        
        cursor.execute("SELECT SUM(monto) FROM transacciones WHERE id_negocio = ? AND metodo_pago LIKE '%Efectivo%' AND tipo = 'ingreso' AND categoria NOT IN ('Cierre de Caja', 'Apertura de Caja')", (id_negocio,))
        efec_ing = cursor.fetchone()[0] or 0.0
        
        cursor.execute("SELECT SUM(monto) FROM transacciones WHERE id_negocio = ? AND metodo_pago LIKE '%Efectivo%' AND tipo = 'gasto'", (id_negocio,))
        efec_gas = cursor.fetchone()[0] or 0.0
        efectivo = efec_ing - efec_gas

        cursor.execute("SELECT SUM(monto) FROM transacciones WHERE id_negocio = ? AND metodo_pago NOT LIKE '%Efectivo%' AND tipo = 'ingreso' AND categoria NOT IN ('Cierre de Caja', 'Apertura de Caja')", (id_negocio,))
        banco_ing = cursor.fetchone()[0] or 0.0
        
        cursor.execute("SELECT SUM(monto) FROM transacciones WHERE id_negocio = ? AND metodo_pago NOT LIKE '%Efectivo%' AND tipo = 'gasto'", (id_negocio,))
        banco_gas = cursor.fetchone()[0] or 0.0
        banco = banco_ing - banco_gas

        cursor.execute("SELECT COUNT(*) FROM agenda WHERE id_negocio = ?", (id_negocio,))
        citas = cursor.fetchone()[0] or 0
        conexion.close()
        return (ingresos - gastos, efectivo, banco, citas)

    def obtener_transacciones(self, id_negocio):
        conexion = self.conectar()
        cursor = conexion.cursor()
        cursor.execute("SELECT id, fecha, tipo, monto, descripcion, metodo_pago, categoria FROM transacciones WHERE id_negocio = ? ORDER BY id DESC", (id_negocio,))
        t = cursor.fetchall()
        conexion.close()
        return t

    def obtener_ventas_pos_filtradas(self, id_negocio, barbero="", metodo=""):
        conexion = self.conectar()
        cursor = conexion.cursor()
        query = "SELECT fecha, descripcion, monto, metodo_pago FROM transacciones WHERE id_negocio = ? AND (descripcion LIKE '%POS:%' OR descripcion LIKE '%Servicio:%' OR descripcion LIKE '%Propina:%')"
        params = [id_negocio]
        
        if barbero:
            query += " AND descripcion LIKE ?"
            params.append(f"%({barbero})%")
        if metodo:
            query += " AND metodo_pago = ?"
            params.append(metodo)
            
        query += " ORDER BY id DESC"
        cursor.execute(query, params)
        v = cursor.fetchall()
        conexion.close()
        return v

    def registrar_venta_pos_carrito(self, id_negocio, cliente, estilista, items, propina, metodo):
        conexion = self.conectar()
        cursor = conexion.cursor()
        
        for servicio_nombre, precio in items:
            cursor.execute("INSERT INTO transacciones (id_negocio, tipo, monto, descripcion, metodo_pago, categoria) VALUES (?, 'ingreso', ?, ?, ?, 'Ventas POS')", 
                           (id_negocio, float(precio), f"POS: {servicio_nombre} ({estilista}) - Cliente: {cliente}", metodo))
            
            cursor.execute("SELECT id, stock FROM servicios WHERE id_negocio = ? AND nombre = ? AND tipo = 'producto'", (id_negocio, servicio_nombre))
            prod = cursor.fetchone()
            if prod:
                nuevo_stock = max(0, prod[1] - 1)
                cursor.execute("UPDATE servicios SET stock = ? WHERE id = ?", (nuevo_stock, prod[0]))

        if propina > 0:
            cursor.execute("INSERT INTO transacciones (id_negocio, tipo, monto, descripcion, metodo_pago, categoria) VALUES (?, 'ingreso', ?, ?, ?, 'Propinas')", 
                           (id_negocio, float(propina), f"Propina: {estilista} - Cliente: {cliente}", metodo))

        cursor.execute("SELECT id, puntos FROM clientes WHERE id_negocio = ? AND nombre = ?", (id_negocio, cliente))
        cli = cursor.fetchone()
        if cli:
            cursor.execute("UPDATE clientes SET puntos = puntos + 10 WHERE id = ?", (cli[0],))
        else:
            cursor.execute("INSERT INTO clientes (id_negocio, nombre, puntos, notas) VALUES (?, ?, 10, 'Cliente frecuente POS')", (id_negocio, cliente))

        # Eliminar la cita de la agenda al cobrar usando coincidencia exacta o parcial
        cursor.execute("DELETE FROM agenda WHERE id_negocio = ? AND (cliente = ? OR ? LIKE '%' || cliente || '%')", (id_negocio, cliente, cliente))

        conexion.commit()
        conexion.close()
        
        conexion = self.conectar()
        cursor = conexion.cursor()
        cursor.execute("SELECT MAX(id) FROM transacciones WHERE id_negocio = ?", (id_negocio,))
        last_id = cursor.fetchone()[0]
        conexion.close()
        return last_id

    def realizar_corte_caja(self, id_negocio, fondo_inicial, efectivo_teorico, efectivo_real, diferencia, notas):
        conexion = self.conectar()
        cursor = conexion.cursor()
        
        cursor.execute("""
            INSERT INTO cierres_caja (id_negocio, fondo_inicial, efectivo_teorico, efectivo_real, diferencia, notas)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (id_negocio, fondo_inicial, efectivo_teorico, efectivo_real, diferencia, notas))
        
        desc_cierre = f"Cierre de Caja - Real: ${efectivo_real:.2f} (Teórico: ${efectivo_teorico:.2f}, Dif: ${diferencia:.2f}) | Notas: {notas}"
        cursor.execute("INSERT INTO transacciones (id_negocio, tipo, monto, descripcion, metodo_pago, categoria) VALUES (?, 'ingreso', ?, ?, 'Efectivo', 'Cierre de Caja')",
                       (id_negocio, efectivo_real, desc_cierre))

        conexion.commit()
        conexion.close()
        self.cerrar_caja_hoy(id_negocio)

    def canjear_puntos_cliente(self, id_negocio, cliente_nombre):
        conexion = self.conectar()
        cursor = conexion.cursor()
        cursor.execute("SELECT puntos_meta FROM config_puntos WHERE id_negocio = ?", (id_negocio,))
        res = cursor.fetchone()
        meta = res[0] if res else 100
        
        cursor.execute("SELECT id, puntos FROM clientes WHERE id_negocio = ? AND nombre = ?", (id_negocio, cliente_nombre))
        cli = cursor.fetchone()
        if cli and cli[1] >= meta:
            nuevos_puntos = cli[1] - meta
            cursor.execute("UPDATE clientes SET puntos = ? WHERE id = ?", (nuevos_puntos, cli[0]))
            conexion.commit()
            conexion.close()
            return True
        conexion.close()
        return False

    def obtener_barberos(self, id_negocio):
        conexion = self.conectar()
        cursor = conexion.cursor()
        cursor.execute("SELECT id, nombre, comision FROM barberos WHERE id_negocio = ?", (id_negocio,))
        b = cursor.fetchall()
        conexion.close()
        return b

    def obtener_servicios(self, id_negocio):
        conexion = self.conectar()
        cursor = conexion.cursor()
        cursor.execute("SELECT id, nombre, precio, tipo, stock, stock_minimo FROM servicios WHERE id_negocio = ?", (id_negocio,))
        s = cursor.fetchall()
        conexion.close()
        return s

    def obtener_lista_citas(self, id_negocio):
        conexion = self.conectar()
        cursor = conexion.cursor()
        cursor.execute("SELECT id, fecha_cita, hora, cliente, telefono, barbero, estado FROM agenda WHERE id_negocio = ? ORDER BY fecha_cita ASC, hora ASC", (id_negocio,))
        c = cursor.fetchall()
        conexion.close()
        return c

    def obtener_citas_hoy(self, id_negocio):
        hoy = str(date.today())
        conexion = self.conectar()
        cursor = conexion.cursor()
        cursor.execute("SELECT id, fecha_cita, hora, cliente, telefono, barbero, estado FROM agenda WHERE id_negocio = ? AND fecha_cita = ? ORDER BY hora ASC", (id_negocio, hoy))
        c = cursor.fetchall()
        conexion.close()
        return c

    def obtener_clientes_pos_hoy(self, id_negocio):
        hoy = str(date.today())
        conexion = self.conectar()
        cursor = conexion.cursor()
        cursor.execute("SELECT DISTINCT cliente, telefono FROM agenda WHERE id_negocio = ? AND fecha_cita = ?", (id_negocio, hoy))
        c = cursor.fetchall()
        conexion.close()
        return c

    def cambiar_estado_cita(self, id_cita, id_negocio, nuevo_estado):
        conexion = self.conectar()
        cursor = conexion.cursor()
        cursor.execute("UPDATE agenda SET estado = ? WHERE id = ? AND id_negocio = ?", (nuevo_estado, id_cita, id_negocio))
        conexion.commit()
        conexion.close()

    def obtener_datos_grafica_finanzas(self, id_negocio):
        conexion = self.conectar()
        cursor = conexion.cursor()
        cursor.execute("""
            SELECT metodo_pago, SUM(monto) 
            FROM transacciones 
            WHERE id_negocio = ? AND tipo = 'ingreso' AND categoria NOT IN ('Cierre de Caja', 'Apertura de Caja')
            GROUP BY metodo_pago
        """, (id_negocio,))
        resultados = cursor.fetchall()
        conexion.close()
        return resultados

    def agregar_cita(self, id_negocio, fecha_cita, hora, cliente, telefono, barbero):
        conexion = self.conectar()
        cursor = conexion.cursor()
        cursor.execute("INSERT INTO agenda (id_negocio, fecha_cita, hora, cliente, telefono, barbero, estado) VALUES (?, ?, ?, ?, ?, ?, 'Agendada')", 
                       (id_negocio, fecha_cita, hora, cliente, telefono, barbero))
        
        cursor.execute("SELECT id FROM clientes WHERE id_negocio = ? AND nombre = ?", (id_negocio, cliente))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO clientes (id_negocio, nombre, telefono, puntos, notas) VALUES (?, ?, ?, 0, 'Agendado en agenda')", 
                           (id_negocio, cliente, telefono))

        conexion.commit()
        conexion.close()

    def eliminar_cita(self, id_cita, id_negocio):
        conexion = self.conectar()
        cursor = conexion.cursor()
        cursor.execute("DELETE FROM agenda WHERE id = ? AND id_negocio = ?", (id_cita, id_negocio))
        conexion.commit()
        conexion.close()

    def obtener_clientes(self, id_negocio):
        conexion = self.conectar()
        cursor = conexion.cursor()
        cursor.execute("SELECT DISTINCT nombre, telefono, notas FROM clientes WHERE id_negocio = ? ORDER BY nombre ASC", (id_negocio,))
        cl = cursor.fetchall()
        conexion.close()
        return cl

    def obtener_cupones(self, id_negocio):
        conexion = self.conectar()
        cursor = conexion.cursor()
        cursor.execute("SELECT id, codigo, tipo, valor FROM cupones WHERE id_negocio = ?", (id_negocio,))
        c = cursor.fetchall()
        conexion.close()
        return c

    def obtener_puntos(self, id_negocio, cliente):
        conexion = self.conectar()
        cursor = conexion.cursor()
        cursor.execute("SELECT puntos FROM clientes WHERE id_negocio = ? AND nombre = ?", (id_negocio, cliente))
        p = cursor.fetchone()
        conexion.close()
        return p[0] if p else 0

    def obtener_meta_puntos(self, id_negocio):
        conexion = self.conectar()
        cursor = conexion.cursor()
        cursor.execute("SELECT puntos_meta FROM config_puntos WHERE id_negocio = ?", (id_negocio,))
        res = cursor.fetchone()
        conexion.close()
        return res[0] if res else 100

    def actualizar_meta_puntos(self, id_negocio, puntos_meta):
        conexion = self.conectar()
        cursor = conexion.cursor()
        cursor.execute("INSERT OR REPLACE INTO config_puntos (id_negocio, puntos_meta) VALUES (?, ?)", (id_negocio, puntos_meta))
        conexion.commit()
        conexion.close()

    def obtener_alertas_inventario(self, id_negocio):
        conexion = self.conectar()
        cursor = conexion.cursor()
        cursor.execute("SELECT nombre, stock, stock_minimo FROM servicios WHERE id_negocio = ? AND tipo = 'producto' AND stock <= stock_minimo", (id_negocio,))
        a = cursor.fetchall()
        conexion.close()
        return a

    def obtener_usuarios(self, id_negocio):
        conexion = self.conectar()
        cursor = conexion.cursor()
        cursor.execute("SELECT id, usuario, rol FROM usuarios WHERE id_negocio = ?", (id_negocio,))
        u = cursor.fetchall()
        conexion.close()
        return u

    def agregar_usuario(self, id_negocio, usuario, password, rol):
        conexion = self.conectar()
        cursor = conexion.cursor()
        pass_hash = generate_password_hash(password)
        cursor.execute("SELECT id FROM usuarios WHERE id_negocio = ? AND usuario = ?", (id_negocio, usuario))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO usuarios (id_negocio, usuario, password, rol, cambiar_password) VALUES (?, ?, ?, ?, 1)", (id_negocio, usuario, pass_hash, rol))
            conexion.commit()
        conexion.close()

    def eliminar_usuario(self, id_usuario):
        conexion = self.conectar()
        cursor = conexion.cursor()
        cursor.execute("DELETE FROM usuarios WHERE id = ?", (id_usuario,))
        conexion.commit()
        conexion.close()

    def agregar_barbero(self, id_negocio, nombre, comision):
        conexion = self.conectar()
        cursor = conexion.cursor()
        cursor.execute("INSERT INTO barberos (id_negocio, nombre, comision) VALUES (?, ?, ?)", (id_negocio, nombre, comision))
        conexion.commit()
        conexion.close()

    def eliminar_barbero(self, id_barbero):
        conexion = self.conectar()
        cursor = conexion.cursor()
        cursor.execute("DELETE FROM barberos WHERE id = ?", (id_barbero,))
        conexion.commit()
        conexion.close()

    def agregar_servicio(self, id_negocio, nombre, precio, tipo, stock, stock_minimo):
        conexion = self.conectar()
        cursor = conexion.cursor()
        cursor.execute("INSERT INTO servicios (id_negocio, nombre, precio, tipo, stock, stock_minimo) VALUES (?, ?, ?, ?, ?, ?)", 
                       (id_negocio, nombre, precio, tipo, stock, stock_minimo))
        conexion.commit()
        conexion.close()

    def agregar_transaccion_con_categoria(self, id_negocio, tipo, monto, descripcion, metodo_pago, categoria):
        conexion = self.conectar()
        cursor = conexion.cursor()
        cursor.execute("INSERT INTO transacciones (id_negocio, tipo, monto, descripcion, metodo_pago, categoria) VALUES (?, ?, ?, ?, ?, ?)", 
                       (id_negocio, tipo, monto, descripcion, metodo_pago, categoria))
        conexion.commit()
        conexion.close()

    def eliminar_transaccion(self, id_transaccion, id_negocio):
        conexion = self.conectar()
        cursor = conexion.cursor()
        cursor.execute("DELETE FROM transacciones WHERE id = ? AND id_negocio = ?", (id_transaccion, id_negocio))
        conexion.commit()
        conexion.close()

    def obtener_reporte_barberos(self, id_negocio):
        barberos = self.obtener_barberos(id_negocio)
        reporte = []
        conexion = self.conectar()
        cursor = conexion.cursor()
        for b in barberos:
            nombre = b[1]
            comision_porcentaje = b[2]
            
            cursor.execute("SELECT descripcion, monto FROM transacciones WHERE id_negocio = ? AND descripcion LIKE ? AND descripcion NOT LIKE '%Propina:%' AND descripcion NOT LIKE '[PAGADO]%'", 
                           (id_negocio, f"%({nombre})%"))
            ventas_servicios = cursor.fetchall()
            
            cursor.execute("SELECT descripcion, monto FROM transacciones WHERE id_negocio = ? AND descripcion LIKE ? AND descripcion NOT LIKE '[PAGADO]%'", 
                           (id_negocio, f"%Propina: {nombre}%"))
            propinas_registros = cursor.fetchall()

            servicios_count = len(ventas_servicios)
            comision_total = 0.0
            propinas_total = sum([m[1] for m in propinas_registros])
            
            for desc, monto in ventas_servicios:
                if comision_porcentaje > 0 and comision_porcentaje <= 100:
                    comision_total += monto * (comision_porcentaje / 100)
                else:
                    comision_total += monto

            total_a_pagar_barbero = comision_total + propinas_total
            reporte.append((nombre, servicios_count, comision_total, propinas_total, total_a_pagar_barbero))
        
        conexion.close()
        return reporte

    def pagar_nomina_dia(self, id_negocio):
        reporte = self.obtener_reporte_barberos(id_negocio)
        total_nomina = sum([r[4] for r in reporte if r[4] > 0])
        
        if total_nomina > 0:
            conexion = self.conectar()
            cursor = conexion.cursor()
            cursor.execute("INSERT INTO transacciones (id_negocio, tipo, monto, descripcion, metodo_pago, categoria) VALUES (?, 'gasto', ?, ?, 'Efectivo', 'Nómina')",
                           (id_negocio, total_nomina, "Pago de Nómina y Comisiones del Día a Barberos"))
            cursor.execute("UPDATE transacciones SET descripcion = '[PAGADO] ' || descripcion WHERE id_negocio = ? AND (descripcion LIKE 'POS:%' OR descripcion LIKE 'Servicio:%' OR descripcion LIKE 'Propina:%') AND descripcion NOT LIKE '[PAGADO]%'", 
                           (id_negocio,))
            conexion.commit()
            conexion.close()
            return reporte
        return []

    def obtener_negocios_saas(self):
        conexion = self.conectar()
        cursor = conexion.cursor()
        cursor.execute("SELECT id, nombre_barberia, dias_restantes, precio_mensual FROM negocios")
        n = cursor.fetchall()
        conexion.close()
        return n

    def registrar_negocio_saas(self, nombre_barberia, usuario, password):
        conexion = self.conectar()
        cursor = conexion.cursor()
        cursor.execute("INSERT INTO negocios (nombre_barberia, dias_restantes, precio_mensual) VALUES (?, 27, 500.0)", (nombre_barberia,))
        id_negocio = cursor.lastrowid
        
        cursor.execute("""
            INSERT INTO ingresos_saas (id_negocio, monto, descripcion) 
            VALUES (?, 500.0, ?)
        """, (id_negocio, f"Registro inicial SaaS - {nombre_barberia}"))
        
        pass_hash = generate_password_hash(password)
        cursor.execute("INSERT INTO usuarios (id_negocio, usuario, password, rol, cambiar_password) VALUES (?, ?, ?, 'admin', 1)", 
                       (id_negocio, usuario, pass_hash))
        
        cursor.execute("INSERT INTO barberos (id_negocio, nombre, comision) VALUES (?, 'Barbero Principal', 50)", (id_negocio,))
        cursor.execute("INSERT INTO servicios (id_negocio, nombre, precio, tipo, stock, stock_minimo) VALUES (?, 'Corte Estándar', 150.0, 'servicio', 0, 5)", (id_negocio,))
        cursor.execute("INSERT OR IGNORE INTO config_puntos (id_negocio, puntos_meta) VALUES (?, 100)", (id_negocio,))
        
        conexion.commit()
        conexion.close()

    def actualizar_precio_y_renovar(self, id_negocio, nuevo_precio, meses_a_sumar):
        conexion = self.conectar()
        cursor = conexion.cursor()
        dias_a_agregar = int(meses_a_sumar) * 27
        
        cursor.execute("""
            UPDATE negocios 
            SET precio_mensual = ?, dias_restantes = dias_restantes + ? 
            WHERE id = ?
        """, (nuevo_precio, dias_a_agregar, id_negocio))
        
        monto_cobrado_renovacion = nuevo_precio * int(meses_a_sumar)
        cursor.execute("SELECT nombre_barberia FROM negocios WHERE id = ?", (id_negocio,))
        res_negocio = cursor.fetchone()
        nombre_barb = res_negocio[0] if res_negocio else "Barbería"
        
        if monto_cobrado_renovacion > 0:
            cursor.execute("""
                INSERT INTO ingresos_saas (id_negocio, monto, descripcion) 
                VALUES (?, ?, ?)
            """, (id_negocio, monto_cobrado_renovacion, f"Renovación por {meses_a_sumar} mes(es) - {nombre_barb}"))
            
        conexion.commit()
        conexion.close()

    def obtener_ingresos_saas_totales(self):
        conexion = self.conectar()
        cursor = conexion.cursor()
        cursor.execute("SELECT SUM(monto) FROM ingresos_saas")
        total = cursor.fetchone()[0] or 0.0
        
        if total == 0.0:
            cursor.execute("SELECT SUM(precio_mensual) FROM negocios")
            total = cursor.fetchone()[0] or 0.0
            
        conexion.close()
        return total

    def obtener_todos_los_usuarios(self):
        conexion = self.conectar()
        cursor = conexion.cursor()
        cursor.execute("""
            SELECT u.id, COALESCE(n.nombre_barberia, 'Global / Superadmin'), u.usuario, u.rol 
            FROM usuarios u 
            LEFT JOIN negocios n ON u.id_negocio = n.id
            ORDER BY n.nombre_barberia ASC, u.usuario ASC
        """)
        usuarios = cursor.fetchall()
        conexion.close()
        return usuarios

    def actualizar_password_usuario_global(self, id_usuario, nueva_password):
        conexion = self.conectar()
        cursor = conexion.cursor()
        pass_hash = generate_password_hash(nueva_password)
        cursor.execute("UPDATE usuarios SET password = ?, cambiar_password = 0 WHERE id = ?", (pass_hash, id_usuario))
        conexion.commit()
        conexion.close()

    def eliminar_usuario_global(self, id_usuario):
        conexion = self.conectar()
        cursor = conexion.cursor()
        cursor.execute("DELETE FROM usuarios WHERE id = ?", (id_usuario,))
        conexion.commit()
        conexion.close()