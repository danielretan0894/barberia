from flask import Flask, render_template, request, redirect, url_for, session
from base_datos import GestorBaseDatos 
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = 'mi_contraseña_secreta_super_segura'
db = GestorBaseDatos()

@app.before_request
def guardia():
    rutas_publicas = ['login', 'login_demo', 'seleccionar_sucursal', 'suscripcion_vencida', 'forzar_cambio_password', 'abrir_caja_diaria_obligatoria']
    if request.endpoint not in rutas_publicas and request.endpoint != 'static':
        if 'usuario_logeado' not in session: 
            return redirect(url_for('login'))
        
        if session.get('es_demo') and 'demo_expiracion' in session:
            if datetime.now().timestamp() > session['demo_expiracion']:
                session.clear()
                return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        usuario_ingresado = request.form['usuario']
        password_ingresada = request.form['password']
        
        sucursales = db.verificar_usuario_multiples_negocios(usuario_ingresado, password_ingresada)
        
        if sucursales:
            conexion = db.conectar()
            cursor = conexion.cursor()
            cursor.execute("SELECT id, cambiar_password FROM usuarios WHERE usuario = ?", (usuario_ingresado,))
            user_db = cursor.fetchone()
            conexion.close()
            
            if user_db:
                session['id_usuario_cambio'] = user_db[0]
                if user_db[1] == 1:
                    return redirect(url_for('forzar_cambio_password'))

            if len(sucursales) == 1:
                rol = sucursales[0][0]
                session.update({
                    'usuario_logeado': usuario_ingresado, 
                    'rol': rol, 
                    'id_negocio': sucursales[0][1], 
                    'nombre_barberia': sucursales[0][2],
                    'es_demo': False
                })
                if rol == 'superadmin':
                    return redirect(url_for('superadmin'))
                return redirect(url_for('inicio'))
            else:
                session['temp_usuario'] = usuario_ingresado
                session['temp_sucursales'] = sucursales
                return redirect(url_for('seleccionar_sucursal'))
        else:
            error = "Usuario o contraseña incorrectos."
            
    return render_template('login.html', error=error)

@app.route('/forzar_cambio_password', methods=['GET', 'POST'])
def forzar_cambio_password():
    error = None
    if 'id_usuario_cambio' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        nueva_pass = request.form['nueva_password']
        if len(nueva_pass) < 8:
            error = "La contraseña debe tener al menos 8 dígitos."
        else:
            db.actualizar_password_usuario_global(session['id_usuario_cambio'], nueva_pass)
            session.pop('id_usuario_cambio', None)
            return redirect(url_for('login'))

    return render_template('cambiar_password.html', error=error)

@app.route('/seleccionar_sucursal', methods=['GET', 'POST'])
def seleccionar_sucursal():
    if 'temp_usuario' not in session:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        id_elegido = int(request.form['id_negocio'])
        for rol, id_neg, nom_barb, cambiar_pass in session['temp_sucursales']:
            if id_neg == id_elegido:
                if cambiar_pass == 1:
                    conexion = db.conectar()
                    cursor = conexion.cursor()
                    cursor.execute("SELECT id FROM usuarios WHERE usuario = ?", (session['temp_usuario'],))
                    user_id = cursor.fetchone()[0]
                    conexion.close()
                    session['id_usuario_cambio'] = user_id
                    return redirect(url_for('forzar_cambio_password'))

                session.update({
                    'usuario_logeado': session['temp_usuario'],
                    'rol': rol,
                    'id_negocio': id_neg,
                    'nombre_barberia': nom_barb,
                    'es_demo': False
                })
                session.pop('temp_usuario', None)
                session.pop('temp_sucursales', None)
                
                if rol == 'superadmin':
                    return redirect(url_for('superadmin'))
                return redirect(url_for('inicio'))
                
    return render_template('seleccionar_sucursal.html', sucursales=session.get('temp_sucursales'))

@app.route('/login_demo')
def login_demo():
    db.asegurar_cuenta_demo()
    db.reiniciar_cuenta_demo()
    res = db.verificar_usuario_multiples_negocios('demo', '12345')
    if res:
        tiempo_expiracion = datetime.now().timestamp() + (60 * 60)
        session.update({
            'usuario_logeado': 'demo', 
            'rol': res[0][0], 
            'id_negocio': res[0][1], 
            'nombre_barberia': res[0][2],
            'es_demo': True,
            'demo_expiracion': tiempo_expiracion
        })
        return redirect(url_for('inicio'))
    return redirect(url_for('login'))

@app.route('/logout')
def logout(): 
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
def inicio(): 
    # Validación estricta: Si el rol es superadmin, redirigir a su panel maestro
    if session.get('rol') == 'superadmin':
        return redirect(url_for('superadmin'))
        
    return render_template('peluqueria.html', 
                           balance_python=db.obtener_resumen(session['id_negocio'])[0], 
                           citas_python=db.obtener_resumen(session['id_negocio'])[3], 
                           agenda_python=db.obtener_lista_citas(session['id_negocio']), 
                           barberos_python=db.obtener_barberos(session['id_negocio']), 
                           servicios_python=db.obtener_servicios(session['id_negocio']), 
                           alertas_python=db.obtener_alertas_inventario(session['id_negocio']))

@app.route('/pos')
def pos(): 
    if session.get('rol') == 'superadmin':
        return redirect(url_for('superadmin'))
        
    id_negocio = session.get('id_negocio')
    rol = session.get('rol')
    if id_negocio and rol in ['admin', 'cajero']:
        fondo_hoy = db.verificar_caja_abierta_hoy(id_negocio)
        if not fondo_hoy:
            return redirect(url_for('abrir_caja_diaria_obligatoria'))
        else:
            session['caja_inicial'] = fondo_hoy

    return render_template('pos.html', 
                           barberos_python=db.obtener_barberos(session['id_negocio']), 
                           servicios_python=db.obtener_servicios(session['id_negocio']),
                           clientes_python=db.obtener_clientes_pos_hoy(session['id_negocio']),
                           agenda_python=db.obtener_citas_hoy(session['id_negocio']))

@app.route('/abrir_caja_diaria', methods=['GET', 'POST'])
def abrir_caja_diaria_obligatoria():
    if session.get('rol') == 'superadmin':
        return redirect(url_for('superadmin'))
        
    if request.method == 'POST':
        monto = float(request.form.get('monto_inicial') or 0)
        db.abrir_caja_hoy(session['id_negocio'], monto)
        session['caja_inicial'] = monto
        return redirect(url_for('pos'))
    return render_template('abrir_caja.html', negocio=session.get('nombre_barberia'))

@app.route('/fijar_caja_inicial', methods=['POST'])
def fijar_caja_inicial():
    monto_inicial = float(request.form.get('monto_inicial') or 0)
    db.abrir_caja_hoy(session['id_negocio'], monto_inicial)
    session['caja_inicial'] = monto_inicial
    return redirect(url_for('pos'))

@app.route('/cerrar_caja_vista')
def cerrar_caja_vista():
    if not session.get('caja_inicial'):
        return redirect(url_for('pos'))
    fondo = float(session.get('caja_inicial') or 0)
    efectivo_neto_ventas = db.obtener_resumen(session['id_negocio'])[1]
    efectivo_teorico = fondo + efectivo_neto_ventas
    return render_template('cerrar_caja.html', fondo=fondo, teorico=efectivo_teorico, negocio=session.get('nombre_barberia'))

@app.route('/arqueo_caja', methods=['POST'])
def arqueo_caja():
    fondo = float(session.get('caja_inicial') or 0)
    efectivo_neto_ventas = db.obtener_resumen(session['id_negocio'])[1]
    efectivo_teorico = fondo + efectivo_neto_ventas
    efectivo_real = float(request.form.get('efectivo_real') or 0)
    diferencia = efectivo_real - efectivo_teorico
    notas = request.form.get('notas_arqueo', 'Sin novedad')
    
    db.realizar_corte_caja(session['id_negocio'], fondo, efectivo_teorico, efectivo_real, diferencia, notas)
    session.pop('caja_inicial', None)
    return redirect(url_for('pos'))

@app.route('/cobrar_pos', methods=['POST'])
def cobrar_pos():
    cliente = request.form.get('nombre_cliente') or 'Mostrador'
    estilista = request.form.get('nombre_barbero') or 'Barbero General'
    propina = float(request.form.get('propina') or 0)
    
    servicios_nombres = request.form.getlist('cart_servicio[]')
    servicios_precios = request.form.getlist('cart_precio[]')
    
    if not servicios_nombres:
        return redirect(url_for('pos'))
        
    items = list(zip(servicios_nombres, servicios_precios))
    metodo_seleccionado = request.form.get('metodo_pago', 'Efectivo')
    
    last_id = None
    if metodo_seleccionado == 'Pago Mixto':
        monto_efectivo = float(request.form.get('mixto_efectivo') or 0)
        monto_banco = float(request.form.get('mixto_banco') or 0)
        
        if monto_efectivo > 0:
            last_id = db.registrar_venta_pos_carrito(
                session['id_negocio'], cliente, estilista, items, propina if monto_banco == 0 else 0, "Mixto (Efectivo)"
            )
        if monto_banco > 0:
            last_id = db.registrar_venta_pos_carrito(
                session['id_negocio'], cliente, estilista, items, propina if monto_efectivo == 0 else 0, "Mixto (Tarjeta/Transf.)"
            )
    else:
        tipo_moneda = request.form.get('tipo_moneda', 'MXN')
        if tipo_moneda == 'USD':
            tipo_cambio = float(request.form.get('tipo_cambio') or 20.0)
            metodo = f"Efectivo USD (T.C. {tipo_cambio})"
        else:
            metodo = metodo_seleccionado

        last_id = db.registrar_venta_pos_carrito(
            session['id_negocio'], cliente, estilista, items, propina, metodo
        )
        
    if last_id:
        return redirect(url_for('ticket', id_venta=last_id))
    return redirect(url_for('pos'))

@app.route('/ticket/<int:id_venta>')
def ticket(id_venta):
    conexion = db.conectar()
    cursor = conexion.cursor()
    cursor.execute("SELECT fecha, descripcion, monto, metodo_pago FROM transacciones WHERE id = ? AND id_negocio = ?", (id_venta, session['id_negocio']))
    v = cursor.fetchone()
    conexion.close()
    return render_template('ticket.html', venta=v, negocio=session.get('nombre_barberia'))

@app.route('/agenda')
def agenda(): 
    if session.get('rol') == 'superadmin':
        return redirect(url_for('superadmin'))
    return render_template('agenda.html', 
                           agenda_python=db.obtener_lista_citas(session['id_negocio']),
                           barberos_python=db.obtener_barberos(session['id_negocio']))

@app.route('/nueva_cita', methods=['POST'])
def nueva_cita():
    db.agregar_cita(
        session['id_negocio'], 
        request.form['fecha_cita'],
        request.form['hora_cita'], 
        request.form['cliente_cita'], 
        request.form['telefono_cita'],
        request.form['barbero_cita']
    )
    return redirect(url_for('agenda'))

@app.route('/eliminar_cita/<int:id_cita>')
def eliminar_cita(id_cita):
    db.eliminar_cita(id_cita, session['id_negocio'])
    return redirect(url_for('agenda'))

@app.route('/clientes')
def clientes(): 
    if session.get('rol') == 'superadmin':
        return redirect(url_for('superadmin'))
    clientes_raw = db.obtener_clientes(session['id_negocio'])
    meta_puntos = db.obtener_meta_puntos(session['id_negocio'])
    clientes_con_puntos = []
    for c in clientes_raw:
        nombre = c[0]
        telefono = c[1]
        notas = c[2]
        puntos = db.obtener_puntos(session['id_negocio'], nombre)
        clientes_con_puntos.append((nombre, telefono, puntos, notas))
        
    return render_template('clientes.html', clientes_python=clientes_con_puntos, meta_puntos=meta_puntos)

@app.route('/canjear_recompensa', methods=['POST'])
def canjear_recompensa():
    cliente = request.form.get('cliente_canje')
    db.canjear_puntos_cliente(session['id_negocio'], cliente)
    return redirect(url_for('clientes'))

@app.route('/finanzas')
def finanzas(): 
    if session.get('rol') == 'superadmin':
        return redirect(url_for('superadmin'))
    return render_template('finanzas.html', 
                           balance_python=db.obtener_resumen(session['id_negocio'])[0], 
                           efectivo_python=db.obtener_resumen(session['id_negocio'])[1], 
                           banco_python=db.obtener_resumen(session['id_negocio'])[2], 
                           transacciones_python=db.obtener_transacciones(session['id_negocio']), 
                           reporte_barberos=db.obtener_reporte_barberos(session['id_negocio']))

@app.route('/nueva_transaccion', methods=['POST'])
def nueva_transaccion():
    db.agregar_transaccion_con_categoria(
        session['id_negocio'], 
        request.form['tipo_transaccion'], 
        float(request.form['monto_transaccion']), 
        request.form['descripcion_transaccion'], 
        request.form['metodo_pago'],
        request.form.get('categoria', 'General')
    )
    return redirect(url_for('finanzas'))

@app.route('/eliminar_transaccion/<int:id_t>')
def eliminar_transaccion_ruta(id_t):
    if session.get('rol') != 'admin':
        return redirect(url_for('finanzas'))
    db.eliminar_transaccion(id_t, session['id_negocio'])
    return redirect(url_for('finanzas'))

@app.route('/pagar_nomina')
def pagar_nomina():
    reporte_pagado = db.pagar_nomina_dia(session['id_negocio'])
    if not reporte_pagado:
        return redirect(url_for('finanzas'))
    total_general = sum([r[4] for r in reporte_pagado])
    return render_template('recibo_nomina.html', reporte=reporte_pagado, total_general=total_general, negocio=session.get('nombre_barberia'))

@app.route('/superadmin')
def superadmin():
    if session.get('rol') != 'superadmin':
        return redirect(url_for('login'))
    negocios = db.obtener_negocios_saas()
    ingresos_globales = db.obtener_ingresos_saas_totales()
    usuarios_globales = db.obtener_todos_los_usuarios()
    return render_template('superadmin.html', 
                           negocios_python=negocios, 
                           ingresos_globales=ingresos_globales,
                           usuarios_globales=usuarios_globales)

@app.route('/registrar_negocio_saas', methods=['POST'])
def registrar_negocio_saas():
    if session.get('rol') != 'superadmin':
        return redirect(url_for('login'))
    db.registrar_negocio_saas(
        request.form['nombre_barberia'],
        request.form['usuario_admin'],
        request.form['password_admin']
    )
    return redirect(url_for('superadmin'))

@app.route('/renovar_negocio_saas', methods=['POST'])
def renovar_negocio_saas():
    if session.get('rol') != 'superadmin':
        return redirect(url_for('login'))
    id_negocio = request.form['id_negocio']
    precio_ingresado = float(request.form.get('precio_mensual') or 0)
    periodo = int(request.form.get('periodo_meses') or 1)
    db.actualizar_precio_y_renovar(id_negocio, precio_ingresado, periodo)
    return redirect(url_for('superadmin'))

@app.route('/actualizar_password_global', methods=['POST'])
def actualizar_password_global():
    if session.get('rol') != 'superadmin':
        return redirect(url_for('login'))
    db.actualizar_password_usuario_global(request.form['id_usuario'], request.form['nueva_password'])
    return redirect(url_for('superadmin'))

@app.route('/eliminar_usuario_global/<int:id_usuario>')
def eliminar_usuario_global(id_usuario):
    if session.get('rol') != 'superadmin':
        return redirect(url_for('login'))
    db.eliminar_usuario_global(id_usuario)
    return redirect(url_for('superadmin'))

@app.route('/historial_pos')
def historial_pos(): 
    if session.get('rol') == 'superadmin':
        return redirect(url_for('superadmin'))
    barbero_filtro = request.args.get('barbero', '')
    metodo_filtro = request.args.get('metodo', '')
    ventas = db.obtener_ventas_pos_filtradas(session['id_negocio'], barbero_filtro, metodo_filtro)
    barberos = db.obtener_barberos(session['id_negocio'])
    return render_template('historial_pos.html', 
                           ventas_python=ventas, 
                           barberos_python=barberos,
                           barbero_seleccionado=barbero_filtro,
                           metodo_seleccionado=metodo_filtro)

@app.route('/inventario')
def inventario(): 
    if session.get('rol') == 'superadmin':
        return redirect(url_for('superadmin'))
    return render_template('inventario.html', 
                           servicios_python=db.obtener_servicios(session['id_negocio']), 
                           alertas_python=db.obtener_alertas_inventario(session['id_negocio']))

@app.route('/ajustes')
def ajustes(): 
    if session.get('rol') == 'superadmin':
        return redirect(url_for('superadmin'))
    return render_template('ajustes.html', 
                           barberos_python=db.obtener_barberos(session['id_negocio']), 
                           usuarios_python=db.obtener_usuarios(session['id_negocio']),
                           cupones_python=db.obtener_cupones(session['id_negocio']),
                           meta_puntos=db.obtener_meta_puntos(session['id_negocio']))

@app.route('/nuevo_usuario', methods=['POST'])
def nuevo_usuario():
    db.agregar_usuario(session['id_negocio'], request.form['nuevo_usuario'], request.form['nuevo_password'], request.form['rol_usuario'])
    return redirect(url_for('ajustes'))

@app.route('/eliminar_usuario/<int:id_usuario>')
def eliminar_usuario_ruta(id_usuario):
    db.eliminar_usuario(id_usuario)
    return redirect(url_for('ajustes'))

@app.route('/nuevo_barbero', methods=['POST'])
def nuevo_barbero():
    db.agregar_barbero(session['id_negocio'], request.form['nombre_barberia'], float(request.form.get('comision_barbero', 50)))
    return redirect(url_for('ajustes'))

@app.route('/eliminar_barbero/<int:id_barbero>')
def eliminar_barbero_ruta(id_barbero):
    db.eliminar_barbero(id_barbero)
    return redirect(url_for('ajustes'))

@app.route('/nuevo_servicio', methods=['POST'])
def nuevo_servicio():
    db.agregar_servicio(session['id_negocio'], request.form['nombre_servicio'], float(request.form['precio_servicio']), request.form['tipo_servicio'], int(request.form.get('stock_inicial', 0)), int(request.form.get('stock_minimo', 5)))
    return redirect(url_for('inventario'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)