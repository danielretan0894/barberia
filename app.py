from flask import Flask, render_template, request, redirect, url_for, session
from base_datos import GestorBaseDatos 
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'mi_contraseña_secreta_super_segura'
db = GestorBaseDatos()

@app.before_request
def guardia():
    rutas_publicas = ['login', 'login_demo', 'seleccionar_sucursal', 'suscripcion_vencida']
    if request.endpoint not in rutas_publicas and request.endpoint != 'static':
        if 'usuario_logeado' not in session: return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        sucursales = db.verificar_usuario_multiples_negocios(request.form['usuario'], request.form['password'])
        if sucursales:
            if sucursales[0][0] == 'superadmin':
                session.update({'usuario_logeado': request.form['usuario'], 'rol': 'superadmin', 'id_negocio': 0})
                return redirect(url_for('superadmin'))
            elif len(sucursales) == 1:
                session.update({'usuario_logeado': request.form['usuario'], 'rol': sucursales[0][0], 'id_negocio': sucursales[0][1], 'nombre_barberia': sucursales[0][2]})
                return redirect(url_for('inicio'))
            else:
                session.update({'temp_usuario': request.form['usuario'], 'temp_sucursales': sucursales})
                return redirect(url_for('seleccionar_sucursal'))
        else:
            error = 'Usuario o contraseña incorrectos.'
    return render_template('login.html', error=error)

@app.route('/seleccionar_sucursal', methods=['GET', 'POST'])
def seleccionar_sucursal():
    if 'temp_sucursales' not in session: return redirect(url_for('login'))
    if request.method == 'POST':
        for s in session['temp_sucursales']:
            if s[1] == int(request.form['id_negocio']):
                session.update({'usuario_logeado': session['temp_usuario'], 'rol': s[0], 'id_negocio': s[1], 'nombre_barberia': s[2]})
                session.pop('temp_usuario', None); session.pop('temp_sucursales', None)
                return redirect(url_for('inicio'))
    return render_template('seleccionar_sucursal.html', sucursales=session['temp_sucursales'])

@app.route('/login_demo')
def login_demo():
    db.asegurar_cuenta_demo()
    res = db.verificar_usuario_multiples_negocios('demo', '12345')
    if res:
        session.update({'usuario_logeado': 'demo', 'rol': res[0][0], 'id_negocio': res[0][1], 'nombre_barberia': res[0][2]})
        return redirect(url_for('inicio'))
    return redirect(url_for('login'))

@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('login'))

@app.route('/')
def inicio(): return render_template('peluqueria.html', balance_python=db.obtener_resumen(session['id_negocio'])[0], citas_python=db.obtener_resumen(session['id_negocio'])[3], agenda_python=db.obtener_lista_citas(session['id_negocio']), barberos_python=db.obtener_barberos(session['id_negocio']), servicios_python=db.obtener_servicios(session['id_negocio']), alertas_python=db.obtener_alertas_inventario(session['id_negocio']))

@app.route('/pos')
def pos(): return render_template('pos.html', barberos_python=db.obtener_barberos(session['id_negocio']), servicios_python=db.obtener_servicios(session['id_negocio']))

@app.route('/cobrar_pos', methods=['POST'])
def cobrar_pos():
    s_p = request.form['servicio_precio'].split('|')
    db.registrar_venta_pos(session['id_negocio'], request.form.get('nombre_cliente') or 'Mostrador', request.form['nombre_barbero'], s_p[0], float(s_p[1]), float(request.form.get('propina') or 0), float(request.form.get('pago_recibido') or 0), 0, 1 if s_p[2]=='servicio' else 0, request.form['metodo_pago'])
    return redirect(url_for('pos'))

@app.route('/agenda')
def agenda(): return render_template('agenda.html', agenda_python=db.obtener_lista_citas(session['id_negocio']))

@app.route('/clientes')
def clientes(): return render_template('clientes.html', clientes_python=db.obtener_clientes(session['id_negocio']), db=db)

@app.route('/finanzas')
def finanzas(): return render_template('finanzas.html', balance_python=db.obtener_resumen(session['id_negocio'])[0], efectivo_python=db.obtener_resumen(session['id_negocio'])[1], banco_python=db.obtener_resumen(session['id_negocio'])[2], transacciones_python=db.obtener_transacciones(session['id_negocio']), reporte_barberos=db.obtener_reporte_barberos(session['id_negocio']))

@app.route('/inventario')
def inventario(): return render_template('inventario.html', servicios_python=db.obtener_servicios(session['id_negocio']), alertas_python=db.obtener_alertas_inventario(session['id_negocio']))

@app.route('/ajustes')
def ajustes(): return render_template('ajustes.html', barberos_python=db.obtener_barberos(session['id_negocio']), usuarios_python=db.obtener_usuarios(session['id_negocio']))

@app.route('/nuevo_usuario', methods=['POST'])
def nuevo_usuario():
    db.agregar_usuario(session['id_negocio'], request.form['nuevo_usuario'], request.form['nuevo_password'], request.form['rol_usuario'])
    return redirect(url_for('ajustes'))

@app.route('/nueva_transaccion', methods=['POST'])
def nueva_transaccion():
    db.agregar_transaccion(session['id_negocio'], request.form['tipo_transaccion'], float(request.form['monto_transaccion']), request.form['descripcion_transaccion'], request.form['metodo_pago'])
    return redirect(url_for('finanzas'))

@app.route('/nuevo_barbero', methods=['POST'])
def nuevo_barbero():
    db.agregar_barbero(session['id_negocio'], request.form['nombre_barbero'], float(request.form.get('comision_barbero', 50)))
    return redirect(url_for('ajustes'))

@app.route('/nuevo_servicio', methods=['POST'])
def nuevo_servicio():
    db.agregar_servicio(session['id_negocio'], request.form['nombre_servicio'], float(request.form['precio_servicio']), request.form['tipo_servicio'], int(request.form.get('stock_inicial', 0)), int(request.form.get('stock_minimo', 5)))
    return redirect(url_for('inventario'))

@app.route('/superadmin')
def superadmin():
    if session.get('rol') != 'superadmin': return redirect(url_for('login'))
    act, ing = db.obtener_finanzas_superadmin()
    return render_template('superadmin.html', negocios=db.obtener_todos_negocios(), alertas=db.obtener_negocios_urgentes(), negocios_activos=act, ingresos_globales=ing, desglose_financiero=db.obtener_desglose_financiero_negocios(), usuarios_globales=db.obtener_todos_los_usuarios())

@app.route('/crear_negocio', methods=['POST'])
def crear_negocio():
    db.crear_nuevo_negocio(request.form['nombre_barberia'], request.form['usuario_admin'], request.form['password_admin'])
    return redirect(url_for('superadmin'))

@app.route('/renovar_negocio/<int:id_negocio>', methods=['POST'])
def renovar_negocio(id_negocio):
    db.renovar_negocio(id_negocio, int(request.form['dias']))
    return redirect(url_for('superadmin'))

@app.route('/eliminar_negocio/<int:id_negocio>')
def eliminar_negocio(id_negocio):
    if session.get('rol') == 'superadmin':
        db.eliminar_negocio_completo(id_negocio)
    return redirect(url_for('superadmin'))

@app.route('/cambiar_password_admin', methods=['POST'])
def cambiar_password_admin():
    db.cambiar_password_usuario(request.form['id_usuario'], request.form['nueva_password'])
    return redirect(url_for('superadmin'))

@app.route('/eliminar_usuario_admin/<int:id_usuario>')
def eliminar_usuario_admin(id_usuario):
    if session.get('rol') == 'superadmin':
        db.eliminar_usuario_global(id_usuario)
    return redirect(url_for('superadmin'))

@app.template_filter('datetime_diff')
def datetime_diff(date_str):
    return datetime.strptime(date_str, "%Y-%m-%d") - datetime.now()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)