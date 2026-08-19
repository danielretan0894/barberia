import sqlite3
from datetime import datetime, timedelta

class GestorBaseDatos:
    def __init__(self, nombre_bd='barberia_saas.db'):
        self.nombre_bd = nombre_bd
        self.crear_tablas()

    def conectar(self):
        return sqlite3.connect(self.nombre_bd)

    def crear_tablas(self):
        conexion = self.conectar()
        cursor = conexion.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS negocios (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre_barberia TEXT, estado_suscripcion TEXT DEFAULT 'activa', fecha_vencimiento TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY AUTOINCREMENT, id_negocio INTEGER, fecha TEXT, tipo TEXT, monto REAL, descripcion TEXT, metodo_pago TEXT DEFAULT 'Efectivo')''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY AUTOINCREMENT, id_negocio INTEGER, cliente TEXT, estilista TEXT, inicio TEXT, fin TEXT, servicio TEXT, precio REAL, propina REAL DEFAULT 0)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS clientes (id INTEGER PRIMARY KEY AUTOINCREMENT, id_negocio INTEGER, nombre TEXT, telefono TEXT, notas TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS barberos (id INTEGER PRIMARY KEY AUTOINCREMENT, id_negocio INTEGER, nombre TEXT, comision REAL DEFAULT 50)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS servicios (id INTEGER PRIMARY KEY AUTOINCREMENT, id_negocio INTEGER, nombre TEXT, precio REAL, tipo TEXT DEFAULT 'servicio', stock INTEGER DEFAULT 0, stock_minimo INTEGER DEFAULT 5)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, id_negocio INTEGER, usuario TEXT, password TEXT, rol TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS ventas_pos (id INTEGER PRIMARY KEY AUTOINCREMENT, id_negocio INTEGER, fecha TEXT, cliente TEXT, estilista TEXT, servicio TEXT, precio REAL, propina REAL, total REAL, efectivo_recibido REAL, cambio REAL, aplica_comision INTEGER DEFAULT 1, metodo_pago TEXT DEFAULT 'Efectivo')''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS lealtad (id INTEGER PRIMARY KEY AUTOINCREMENT, id_negocio INTEGER, nombre_cliente TEXT, puntos INTEGER DEFAULT 0)''')
        
        cursor.execute("SELECT COUNT(*) FROM usuarios WHERE rol = 'superadmin'")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO usuarios (id_negocio, usuario, password, rol) VALUES (0, 'master', 'master123', 'superadmin')")
        conexion.commit()
        conexion.close()

    def verificar_usuario_multiples_negocios(self, usuario, password):
        conexion = self.conectar()
        cursor = conexion.cursor()
        cursor.execute("""
            SELECT u.rol, u.id_negocio, n.nombre_barberia 
            FROM usuarios u 
            LEFT JOIN negocios n ON u.id_negocio = n.id 
            WHERE u.usuario = ? AND u.password = ?
        """, (usuario, password))
        res = cursor.fetchall()
        conexion.close()
        return res

    def verificar_suscripcion(self, id_negocio):
        conexion = self.conectar()
        cursor = conexion.cursor()
        cursor.execute("SELECT estado_suscripcion, fecha_vencimiento FROM negocios WHERE id = ?", (id_negocio,))
        res = cursor.fetchone()
        conexion.close()
        if res:
            return 'vencida' if datetime.now() > datetime.strptime(res[1], "%Y-%m-%d") else res[0]
        return 'inactiva'

    def obtener_resumen(self, id_negocio):
        conexion = self.conectar()
        cursor = conexion.cursor()
        try:
            cursor.execute("SELECT tipo, monto, metodo_pago FROM finanzas WHERE id_negocio = ?", (id_negocio,))
            efectivo, banco = 0, 0
            for tipo, monto, metodo in cursor.fetchall():
                if tipo == 'ingreso':
                    if metodo == 'Efectivo': efectivo += monto
                    else: banco += monto
                else:
                    if metodo == 'Efectivo': efectivo -= monto
                    else: banco -= monto
            cursor.execute("SELECT precio, propina, IFNULL(b.comision, 50), IFNULL(c.aplica_comision, 1) FROM ventas_pos c LEFT JOIN barberos b ON c.estilista = b.nombre AND c.id_negocio = b.id_negocio WHERE c.id_negocio = ?", (id_negocio,))
            pagos = cursor.fetchall()
            nomina = sum((p[0] * (p[2] / 100) if p[3] == 1 else 0) + p[1] for p in pagos)
            balance_total = (efectivo + banco) - nomina
        except:
            balance_total, efectivo, banco = 0, 0, 0
        cursor.execute("SELECT COUNT(*) FROM citas WHERE id_negocio = ?", (id_negocio,))
        total_citas = cursor.fetchone()[0]
        conexion.close()
        return round(balance_total, 2), round(efectivo, 2), round(banco, 2), total_citas

    def registrar_venta_pos(self, id_neg, cli, est, serv, prec, prop, efec, camb, com, met):
        conexion = self.conectar()
        cursor = conexion.cursor()
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
        cursor.execute("INSERT INTO ventas_pos (id_negocio, fecha, cliente, estilista, servicio, precio, propina, total, efectivo_recibido, cambio, aplica_comision, metodo_pago) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (id_neg, fecha, cli, est, serv, prec, prop, prec+prop, efec, camb, com, met))
        cursor.execute("INSERT INTO finanzas (id_negocio, fecha, tipo, monto, descripcion, metodo_pago) VALUES (?,?,?,?,?,?)", (id_neg, fecha, 'ingreso', prec, f"POS: {serv}", met))
        if prop > 0: cursor.execute("INSERT INTO finanzas (id_negocio, fecha, tipo, monto, descripcion, metodo_pago) VALUES (?,?,?,?,?,?)", (id_neg, fecha, 'ingreso', prop, "Propina", met))
        if com == 1: self.sumar_puntos_lealtad(id_neg, cli)
        if com == 0: cursor.execute("UPDATE servicios SET stock = stock - 1 WHERE nombre = ? AND id_negocio = ?", (serv, id_neg))
        conexion.commit()
        conexion.close()

    def sumar_puntos_lealtad(self, id_neg, cli):
        conexion = self.conectar()
        cursor = conexion.cursor()
        cursor.execute("SELECT puntos FROM lealtad WHERE id_negocio = ? AND nombre_cliente = ?", (id_neg, cli))
        if cursor.fetchone(): cursor.execute("UPDATE lealtad SET puntos = puntos + 1 WHERE id_negocio = ? AND nombre_cliente = ?", (id_neg, cli))
        else: cursor.execute("INSERT INTO lealtad (id_negocio, nombre_cliente, puntos) VALUES (?, ?, 1)", (id_neg, cli))
        conexion.commit()
        conexion.close()

    def obtener_puntos(self, id_neg, cli):
        conexion = self.conectar()
        cursor = conexion.cursor()
        cursor.execute("SELECT puntos FROM lealtad WHERE id_negocio = ? AND nombre_cliente = ?", (id_neg, cli))
        res = cursor.fetchone()
        conexion.close()
        return res[0] if res else 0

    def obtener_alertas_inventario(self, id_neg):
        conexion = self.conectar()
        cursor = conexion.cursor()
        cursor.execute("SELECT nombre, stock, stock_minimo FROM servicios WHERE id_negocio = ? AND tipo = 'producto' AND stock <= stock_minimo", (id_neg,))
        res = cursor.fetchall()
        conexion.close()
        return res

    def agendar_cita_simple(self, id_negocio, nombre_cliente, estilista, fecha_hora, servicio, duracion_minutos):
        conexion = self.conectar()
        cursor = conexion.cursor()
        inicio_dt = datetime.strptime(fecha_hora, "%Y-%m-%d %H:%M")
        fin_dt = inicio_dt + timedelta(minutes=duracion_minutos)
        cursor.execute("INSERT INTO citas (id_negocio, cliente, estilista, inicio, fin, servicio, precio, propina) VALUES (?, ?, ?, ?, ?, ?, 0, 0)", (id_negocio, nombre_cliente, estilista, inicio_dt.strftime("%Y-%m-%d %H:%M"), fin_dt.strftime("%Y-%m-%d %H:%M"), servicio))
        conexion.commit()
        conexion.close()

    def obtener_lista_citas(self, id_negocio):
        conexion = self.conectar()
        cursor = conexion.cursor()
        cursor.execute("SELECT inicio, cliente, servicio, estilista FROM citas WHERE id_negocio = ? ORDER BY inicio ASC", (id_negocio,))
        res = cursor.fetchall()
        conexion.close()
        return res

    def obtener_clientes(self, id_negocio):
        conexion = self.conectar()
        cursor = conexion.cursor()
        cursor.execute("SELECT nombre, telefono, notas FROM clientes WHERE id_negocio = ? ORDER BY nombre ASC", (id_negocio,))
        res = cursor.fetchall()
        conexion.close()
        return res

    def obtener_barberos(self, id_negocio):
        conexion = self.conectar()
        cursor = conexion.cursor()
        cursor.execute("SELECT id, nombre, comision FROM barberos WHERE id_negocio = ? ORDER BY nombre ASC", (id_negocio,))
        res = cursor.fetchall()
        conexion.close()
        return res

    def agregar_barbero(self, id_negocio, nombre, comision):
        conexion = self.conectar()
        cursor = conexion.cursor()
        cursor.execute("INSERT INTO barberos (id_negocio, nombre, comision) VALUES (?, ?, ?)", (id_negocio, nombre, comision))
        conexion.commit()
        conexion.close()

    def eliminar_barbero(self, id_negocio, id_barbero):
        conexion = self.conectar()
        cursor = conexion.cursor()
        cursor.execute("DELETE FROM barberos WHERE id = ? AND id_negocio = ?", (id_barbero, id_negocio))
        conexion.commit()
        conexion.close()

    def obtener_servicios(self, id_negocio):
        conexion = self.conectar()
        cursor = conexion.cursor()
        cursor.execute("SELECT id, nombre, precio, IFNULL(tipo, 'servicio'), IFNULL(stock, 0), IFNULL(stock_minimo, 5) FROM servicios WHERE id_negocio = ? ORDER BY nombre ASC", (id_negocio,))
        res = cursor.fetchall()
        conexion.close()
        return res

    def agregar_servicio(self, id_negocio, nombre, precio, tipo, stock, stock_minimo):
        conexion = self.conectar()
        cursor = conexion.cursor()
        cursor.execute("INSERT INTO servicios (id_negocio, nombre, precio, tipo, stock, stock_minimo) VALUES (?, ?, ?, ?, ?, ?)", (id_negocio, nombre, precio, tipo, stock, stock_minimo))
        conexion.commit()
        conexion.close()

    def eliminar_servicio(self, id_negocio, id_servicio):
        conexion = self.conectar()
        cursor = conexion.cursor()
        cursor.execute("DELETE FROM servicios WHERE id = ? AND id_negocio = ?", (id_servicio, id_negocio))
        conexion.commit()
        conexion.close()

    def obtener_usuarios(self, id_negocio):
        conexion = self.conectar()
        cursor = conexion.cursor()
        cursor.execute("SELECT id, usuario, rol FROM usuarios WHERE id_negocio = ? ORDER BY rol ASC", (id_negocio,))
        res = cursor.fetchall()
        conexion.close()
        return res

    def agregar_usuario(self, id_negocio, usuario, password, rol):
        conexion = self.conectar()
        cursor = conexion.cursor()
        cursor.execute("INSERT INTO usuarios (id_negocio, usuario, password, rol) VALUES (?, ?, ?, ?)", (id_negocio, usuario, password, rol))
        conexion.commit()
        conexion.close()

    def eliminar_usuario(self, id_negocio, id_usuario):
        conexion = self.conectar()
        cursor = conexion.cursor()
        cursor.execute("DELETE FROM usuarios WHERE id = ? AND id_negocio = ?", (id_usuario, id_negocio))
        conexion.commit()
        conexion.close()

    def agregar_transaccion(self, id_negocio, tipo, monto, descripcion, metodo_pago):
        conexion = self.conectar()
        cursor = conexion.cursor()
        fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M")
        cursor.execute("INSERT INTO finanzas (id_negocio, fecha, tipo, monto, descripcion, metodo_pago) VALUES (?, ?, ?, ?, ?, ?)", (id_negocio, fecha_actual, tipo, monto, descripcion, metodo_pago))
        conexion.commit()
        conexion.close()

    def obtener_transacciones(self, id_negocio):
        conexion = self.conectar()
        cursor = conexion.cursor()
        cursor.execute("SELECT IFNULL(fecha, 'N/A'), tipo, monto, descripcion, IFNULL(metodo_pago, 'Efectivo') FROM finanzas WHERE id_negocio = ? ORDER BY id DESC", (id_negocio,))
        res = cursor.fetchall()
        conexion.close()
        return res

    def obtener_reporte_barberos(self, id_negocio):
        conexion = self.conectar()
        cursor = conexion.cursor()
        cursor.execute("""
            SELECT c.estilista, COUNT(c.id), IFNULL(SUM(CASE WHEN IFNULL(c.aplica_comision, 1) = 1 THEN c.precio ELSE 0 END), 0), IFNULL(SUM(c.propina), 0), IFNULL(b.comision, 50)
            FROM ventas_pos c LEFT JOIN barberos b ON c.estilista = b.nombre AND c.id_negocio = b.id_negocio WHERE c.id_negocio = ? GROUP BY c.estilista
        """, (id_negocio,))
        res = cursor.fetchall()
        conexion.close()
        return res

    def obtener_todos_negocios(self):
        conexion = self.conectar()
        cursor = conexion.cursor()
        cursor.execute("SELECT id, nombre_barberia, estado_suscripcion, fecha_vencimiento FROM negocios ORDER BY id ASC")
        res = cursor.fetchall()
        conexion.close()
        return res

    def crear_nuevo_negocio(self, nombre_barberia, usuario_admin, password_admin):
        conexion = self.conectar()
        cursor = conexion.cursor()
        fecha_venc = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        cursor.execute("INSERT INTO negocios (nombre_barberia, estado_suscripcion, fecha_vencimiento) VALUES (?, 'activa', ?)", (nombre_barberia, fecha_venc))
        nuevo_id = cursor.lastrowid
        cursor.execute("INSERT INTO usuarios (id_negocio, usuario, password, rol) VALUES (?, ?, ?, 'admin')", (nuevo_id, usuario_admin, password_admin))
        conexion.commit()
        conexion.close()

    def renovar_negocio(self, id_negocio, dias_extra):
        conexion = self.conectar()
        cursor = conexion.cursor()
        cursor.execute("SELECT fecha_vencimiento FROM negocios WHERE id = ?", (id_negocio,))
        fecha_actual = datetime.strptime(cursor.fetchone()[0], "%Y-%m-%d")
        nueva_fecha = (datetime.now() if datetime.now() > fecha_actual else fecha_actual) + timedelta(days=dias_extra)
        cursor.execute("UPDATE negocios SET fecha_vencimiento = ?, estado_suscripcion = 'activa' WHERE id = ?", (nueva_fecha.strftime("%Y-%m-%d"), id_negocio))
        conexion.commit()
        conexion.close()

    def eliminar_negocio_completo(self, id_negocio):
        conexion = self.conectar()
        cursor = conexion.cursor()
        cursor.execute("DELETE FROM negocios WHERE id = ?", (id_negocio,))
        cursor.execute("DELETE FROM usuarios WHERE id_negocio = ?", (id_negocio,))
        cursor.execute("DELETE FROM finanzas WHERE id_negocio = ?", (id_negocio,))
        cursor.execute("DELETE FROM citas WHERE id_negocio = ?", (id_negocio,))
        cursor.execute("DELETE FROM clientes WHERE id_negocio = ?", (id_negocio,))
        cursor.execute("DELETE FROM barberos WHERE id_negocio = ?", (id_negocio,))
        cursor.execute("DELETE FROM servicios WHERE id_negocio = ?", (id_negocio,))
        cursor.execute("DELETE FROM ventas_pos WHERE id_negocio = ?", (id_negocio,))
        cursor.execute("DELETE FROM lealtad WHERE id_negocio = ?", (id_negocio,))
        conexion.commit()
        conexion.close()

    def obtener_negocios_urgentes(self):
        conexion = self.conectar()
        cursor = conexion.cursor()
        cursor.execute("SELECT id, nombre_barberia, fecha_vencimiento FROM negocios")
        urgentes = []
        for n in cursor.fetchall():
            dias_restantes = (datetime.strptime(n[2], "%Y-%m-%d") - datetime.now()).days
            if dias_restantes <= 10: urgentes.append({'id': n[0], 'nombre': n[1], 'dias': dias_restantes})
        conexion.close()
        return urgentes

    def asegurar_cuenta_demo(self):
        conexion = self.conectar()
        cursor = conexion.cursor()
        cursor.execute("SELECT id FROM negocios WHERE nombre_barberia = 'Demo Barber'")
        if not cursor.fetchone():
            cursor.execute("INSERT INTO negocios (nombre_barberia, estado_suscripcion, fecha_vencimiento) VALUES ('Demo Barber', 'activa', '2030-01-01')")
            id_demo = cursor.lastrowid
            cursor.execute("INSERT INTO usuarios (id_negocio, usuario, password, rol) VALUES (?, 'demo', '12345', 'admin')", (id_demo,))
            conexion.commit()
            self.crear_datos_demo(id_demo)
        conexion.close()

    def crear_datos_demo(self, id_negocio):
        conexion = self.conectar()
        cursor = conexion.cursor()
        servicios = [('Corte Clásico', 150, 'servicio', 0, 5), ('Cera Mate', 200, 'producto', 20, 5)]
        for s in servicios: cursor.execute("INSERT INTO servicios (id_negocio, nombre, precio, tipo, stock, stock_minimo) VALUES (?,?,?,?,?,?)", (id_negocio, s[0], s[1], s[2], s[3], s[4]))
        conexion.commit()
        conexion.close()

    def obtener_finanzas_superadmin(self):
        conexion = self.conectar()
        cursor = conexion.cursor()
        cursor.execute("SELECT COUNT(*) FROM negocios WHERE estado_suscripcion = 'activa'")
        activas = cursor.fetchone()[0]
        cursor.execute("SELECT SUM(monto) FROM finanzas")
        total = cursor.fetchone()[0] or 0.0
        conexion.close()
        return activas, round(total, 2)

    def obtener_desglose_financiero_negocios(self):
        conexion = self.conectar()
        cursor = conexion.cursor()
        cursor.execute("SELECT n.nombre_barberia, IFNULL(SUM(f.monto), 0) FROM negocios n LEFT JOIN finanzas f ON n.id = f.id_negocio AND f.tipo = 'ingreso' GROUP BY n.id")
        res = cursor.fetchall()
        conexion.close()
        return res

    def obtener_todos_los_usuarios(self):
        conexion = self.conectar()
        cursor = conexion.cursor()
        cursor.execute("SELECT u.id, u.usuario, u.password, u.rol, n.nombre_barberia FROM usuarios u JOIN negocios n ON u.id_negocio = n.id")
        res = cursor.fetchall()
        conexion.close()
        return res

    def cambiar_password_usuario(self, id_usuario, nueva_password):
        conexion = self.conectar()
        cursor = conexion.cursor()
        cursor.execute("UPDATE usuarios SET password = ? WHERE id = ?", (nueva_password, id_usuario))
        conexion.commit()
        conexion.close()

    def eliminar_usuario_global(self, id_usuario):
        conexion = self.conectar()
        cursor = conexion.cursor()
        cursor.execute("DELETE FROM usuarios WHERE id = ? AND rol != 'superadmin'", (id_usuario,))
        conexion.commit()
        conexion.close()