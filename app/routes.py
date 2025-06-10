from flask import Blueprint, request, jsonify
from .models import db, User, Role, Book, Cliente, Prestamo
from functools import wraps
from datetime import datetime, timedelta
import re
from .schemas import (
    user_schema, users_schema, user_login_schema,
    role_schema, roles_schema,
    book_schema, books_schema,
    cliente_schema, clientes_schema,
    prestamo_schema, prestamos_schema
)

#----Blueprints-----------
auth_bp = Blueprint("auth", __name__, url_prefix="/auth")
users_bp = Blueprint("users", __name__, url_prefix="/users")
roles_bp = Blueprint("roles", __name__, url_prefix="/roles")
books_bp = Blueprint("books", __name__, url_prefix="/libros")
clientes_bp = Blueprint("clientes", __name__, url_prefix="/clientes")
prestamos_bp = Blueprint("prestamos", __name__, url_prefix="/prestamos")
reportes_bp = Blueprint("reportes", __name__, url_prefix="/reportes")

# -------- Rutas de Autenticación --------
@auth_bp.route("/login", methods=["POST"])
def login():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'message': 'Usuario y contraseña son requeridas'}), 400
        
        user = User.query.filter_by(username=username).first()
        
        if not user or user.password != password:
            return jsonify({'message': 'credenciales invalidas'}), 401
        
        return jsonify({
            'message': 'Inicio correcto',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role.name,
                'role_id': user.role_id
            }
        }), 200
        
    except Exception as e:
        return jsonify({'message': 'Inicio incorrecto', 'error': str(e)}), 500

# -------- Decorador para verificar rol admin --------
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            return jsonify({'message': 'ID de usuario requerido'}), 401
            
        user = User.query.get(user_id)
        if not user or user.role.name != 'admin':
            return jsonify({'message': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function

# -------- Decorador para verificar rol gestor o admin --------
def manager_or_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            return jsonify({'message': 'ID de usuario requerido'}), 401
            
        user = User.query.get(user_id)
        if not user or user.role.name not in ['admin', 'gestor']:
            return jsonify({'message': 'Acceso denegado. Rol de gestor o administrador requerido'}), 403
        return f(*args, **kwargs)
    return decorated_function

def get_real_availability(libro_id):
    """Calcula la disponibilidad real de un libro basada en préstamos activos"""
    libro = Book.query.get(libro_id)
    if not libro:
        return 0
    
    prestamos_activos = Prestamo.query.filter_by(
        libro_id=libro_id,
        estado='activo'
    ).count()
    
    return max(0, libro.cantidad_disponible - prestamos_activos)

# -------- Rutas de Usuarios --------
@users_bp.route("/", methods=["POST"])
@admin_required
def add_user():
    try:
        data = request.get_json()
        
        role_id = data.get('role_id')
        role = Role.query.get(role_id)
        if not role:
            return jsonify({'message': 'Rol ID incorrecto'}), 400
            
        if User.query.filter_by(username=data.get('username')).first():
            return jsonify({'message': 'Nombre de usuario ya existe'}), 400
            
        if User.query.filter_by(email=data.get('email')).first():
            return jsonify({'message': 'Email ya existente'}), 400
        
        new_user = user_login_schema.load(data)
        db.session.add(new_user)
        db.session.commit()
        return user_schema.dump(new_user), 201
        
    except Exception as e:
        return jsonify({'message': 'Error creando usuario', 'error': str(e)}), 500
    
@users_bp.route("/", methods=["GET"])
def get_users():
    return users_schema.dump(User.query.all()), 200

@users_bp.route("/<int:user_id>", methods=["GET"])
def get_user(user_id):
    user = User.query.get_or_404(user_id)
    return user_schema.dump(user), 200

@users_bp.route("/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return "", 204

@users_bp.route("/<int:user_id>", methods=["PUT"])
@admin_required
def update_user(user_id):
    try:
        data = request.get_json()
        user = User.query.get_or_404(user_id)
        
        if 'username' in data:
            if User.query.filter(User.username == data['username'], User.id != user_id).first():
                return jsonify({'message': 'Nombre de usuario ya existe'}), 400
            user.username = data['username']
        
        if 'email' in data:
            if User.query.filter(User.email == data['email'], User.id != user_id).first():
                return jsonify({'message': 'Email ya existente'}), 400
            user.email = data['email']
        
        if 'role_id' in data:
            if not Role.query.get(data['role_id']):
                return jsonify({'message': 'Rol ID incorrecto'}), 400
            user.role_id = data['role_id']
        
        if 'password' in data and data['password']:
            user.password = data['password']
        
        db.session.commit()
        return user_schema.dump(user), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Error actualizando usuario', 'error': str(e)}), 500

# -------- Rutas de Roles --------
@roles_bp.route("/", methods=["GET"])
def get_roles():
    return roles_schema.dump(Role.query.all()), 200

# -------- Rutas de Libros --------
@books_bp.route("/", methods=["POST"])
@manager_or_admin_required
def add_book():
    try:
        data = request.get_json()
        
        if not data.get('titulo') or not data.get('autor') or not data.get('isbn'):
            return jsonify({'message': 'Título, autor e ISBN son requeridos'}), 400
            
        if Book.query.filter_by(isbn=data.get('isbn')).first():
            return jsonify({'message': 'Ya existe un libro con este ISBN'}), 400
            
        if 'cantidad_disponible' in data and data['cantidad_disponible'] < 0:
            return jsonify({'message': 'La cantidad disponible no puede ser negativa'}), 400
        
        new_book = book_schema.load(data)
        db.session.add(new_book)
        db.session.commit()
        return book_schema.dump(new_book), 201
        
    except Exception as e:
        return jsonify({'message': 'Error al crear libro', 'error': str(e)}), 500
    
@books_bp.route("/", methods=["GET"])
def get_books():
    """Devuelve libros con disponibilidad real calculada"""
    libros = Book.query.all()
    libros_data = []
    
    for libro in libros:
        libro_dict = book_schema.dump(libro)
        disponibilidad_real = get_real_availability(libro.id)
        libro_dict['disponibilidad_real'] = disponibilidad_real
        libros_data.append(libro_dict)
    
    return jsonify(libros_data), 200


@books_bp.route("/<int:book_id>", methods=["GET"])
def get_book(book_id):
    book = Book.query.get_or_404(book_id)
    book_data = book_schema.dump(book)
    book_data['disponibilidad_real'] = get_real_availability(book_id)
    return book_data, 200

@books_bp.route("/<int:book_id>", methods=["DELETE"])
@manager_or_admin_required
def delete_book(book_id):
    try:
        print(f"Intentando eliminar libro con ID: {book_id}")
        libro = Book.query.get_or_404(book_id)
        print(f"Libro encontrado: {libro.titulo}")
        prestamos_activos = Prestamo.query.filter_by(
            libro_id=libro.id,
            estado='activo'
        ).all()
        
        print(f"Número de préstamos activos encontrados: {len(prestamos_activos)}")
        
        if prestamos_activos:
            prestamo_activo = prestamos_activos[0] 
            print(f"Libro tiene préstamo activo para cliente: {prestamo_activo.cliente.nombre}")
            return jsonify({
                'message': 'No se puede eliminar el libro porque está prestado',
                'cliente': prestamo_activo.cliente.nombre,
                'prestamos_activos': len(prestamos_activos)
            }), 400
        
        print("No hay préstamos activos, procediendo a eliminar...")
        
        prestamos_historicos = Prestamo.query.filter_by(
            libro_id=libro.id,
            estado='devuelto'
        ).all()
        
        print(f"Préstamos históricos encontrados: {len(prestamos_historicos)}")
        
        if prestamos_historicos:
            print("Eliminando préstamos históricos...")
            for prestamo in prestamos_historicos:
                db.session.delete(prestamo)
        
        verificacion_final = Prestamo.query.filter_by(
            libro_id=libro.id,
            estado='activo'
        ).count()
        
        if verificacion_final > 0:
            print(f"ADVERTENCIA: Se encontraron {verificacion_final} préstamos activos en verificación final")
            return jsonify({
                'message': 'Error de consistencia: Se detectaron préstamos activos en verificación final',
                'prestamos_activos': verificacion_final
            }), 400
        
        print("Eliminando libro...")
        db.session.delete(libro)
        db.session.commit()
        print("Libro eliminado exitosamente")
        
        return "", 204
        
    except Exception as e:
        print(f"Error completo: {str(e)}")
        print(f"Tipo de error: {type(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        db.session.rollback()
        return jsonify({
            'message': 'Error al eliminar libro', 
            'error': str(e),
            'type': str(type(e))
        }), 500

@books_bp.route("/<int:book_id>", methods=["PUT"])
@manager_or_admin_required
def update_book(book_id):
    try:
        data = request.get_json()
        book = Book.query.get_or_404(book_id)
        
        if 'cantidad_disponible' in data:
            nueva_cantidad = data['cantidad_disponible']
            
            if nueva_cantidad < 0:
                return jsonify({'message': 'La cantidad disponible no puede ser negativa'}), 400
            
            prestamos_activos = Prestamo.query.filter_by(
                libro_id=book_id,
                estado='activo'
            ).count()
            
            if nueva_cantidad < prestamos_activos:
                return jsonify({
                    'message': f'No se puede reducir la cantidad a {nueva_cantidad}. Hay {prestamos_activos} préstamos activos de este libro.'
                }), 400
                
        if 'titulo' in data:
            book.titulo = data['titulo']
        
        if 'autor' in data:
            book.autor = data['autor']
            
        if 'editorial' in data:
            book.editorial = data['editorial']
            
        if 'anio_publicacion' in data:
            book.anio_publicacion = data['anio_publicacion']
            
        if 'isbn' in data:
            book.isbn = data['isbn']
            
        if 'cantidad_disponible' in data:
            book.cantidad_disponible = data['cantidad_disponible']
        
        db.session.commit()
        return book_schema.dump(book), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Error al actualizar libro', 'error': str(e)}), 500

# -------- Rutas de Clientes --------
@clientes_bp.route("/", methods=["POST"])
@manager_or_admin_required
def add_cliente():
    try:
        data = request.get_json()
        
        if not data.get('nombre') or not data.get('numero_identificacion'):
            return jsonify({'message': 'Nombre y número de identificación son requeridos'}), 400
            
        if len(data.get('numero_identificacion', '')) != 13:
            return jsonify({'message': 'El número de identificación debe tener 13 dígitos'}), 400
            
        if Cliente.query.filter_by(numero_identificacion=data.get('numero_identificacion')).first():
            return jsonify({'message': 'Ya existe un cliente con este número de identificación'}), 400
            
        if not re.match(r"[^@]+@[^@]+\.[^@]+", data.get('correo', '')):
            return jsonify({'message': 'El correo electrónico no tiene un formato válido'}), 400
        
        new_cliente = cliente_schema.load(data)
        db.session.add(new_cliente)
        db.session.commit()
        return cliente_schema.dump(new_cliente), 201
        
    except Exception as e:
        return jsonify({'message': 'Error al crear cliente', 'error': str(e)}), 500
    
@clientes_bp.route("/", methods=["GET"])
def get_clientes():
    return clientes_schema.dump(Cliente.query.all()), 200

@clientes_bp.route("/<int:cliente_id>", methods=["GET"])
def get_cliente(cliente_id):
    cliente = Cliente.query.get_or_404(cliente_id)
    return cliente_schema.dump(cliente), 200

@clientes_bp.route("/<int:cliente_id>", methods=["DELETE"])
@manager_or_admin_required
def delete_cliente(cliente_id):
    try:
        print(f"Intentando eliminar cliente con ID: {cliente_id}")
        cliente = Cliente.query.get_or_404(cliente_id)
        print(f"Cliente encontrado: {cliente.nombre}")
        
        prestamo_activo = Prestamo.query.filter_by(
            cliente_id=cliente.id,
            estado='activo'
        ).first()
        
        print(f"Préstamos activos encontrados: {prestamo_activo}")
        
        if prestamo_activo:
            print(f"Cliente tiene préstamo activo del libro: {prestamo_activo.libro.titulo}")
            return jsonify({
                'message': 'No se puede eliminar el cliente porque tiene libros prestados',
                'libro': prestamo_activo.libro.titulo
            }), 400
        
        print("No hay préstamos activos, procediendo a eliminar...")
        
        prestamos_historicos = Prestamo.query.filter_by(cliente_id=cliente.id).all()
        print(f"Préstamos históricos encontrados: {len(prestamos_historicos)}")
        
        if prestamos_historicos:
            print("Eliminando préstamos históricos...")
            for prestamo in prestamos_historicos:
                db.session.delete(prestamo)
        
        print("Eliminando cliente...")
        db.session.delete(cliente)
        db.session.commit()
        print("Cliente eliminado exitosamente")
        
        return "", 204
        
    except Exception as e:
        print(f"Error completo: {str(e)}")
        print(f"Tipo de error: {type(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        db.session.rollback()
        return jsonify({
            'message': 'Error al eliminar cliente', 
            'error': str(e),
            'type': str(type(e))
        }), 500

@clientes_bp.route("/<int:cliente_id>", methods=["PUT"])
@manager_or_admin_required
def update_cliente(cliente_id):
    try:
        data = request.get_json()
        cliente = Cliente.query.get_or_404(cliente_id)
        
        if 'numero_identificacion' in data:
            if len(data['numero_identificacion']) != 13:
                return jsonify({'message': 'El número de identificación debe tener 13 dígitos'}), 400
                
            if Cliente.query.filter(Cliente.numero_identificacion == data['numero_identificacion'], Cliente.id != cliente_id).first():
                return jsonify({'message': 'Ya existe un cliente con este número de identificación'}), 400
        
        if 'correo' in data and not re.match(r"[^@]+@[^@]+\.[^@]+", data['correo']):
            return jsonify({'message': 'El correo electrónico no tiene un formato válido'}), 400
        
        if 'nombre' in data:
            cliente.nombre = data['nombre']
            
        if 'apellido' in data:
            cliente.apellido = data['apellido']
            
        if 'correo' in data:
            cliente.correo = data['correo']
            
        if 'telefono' in data:
            cliente.telefono = data['telefono']
            
        if 'numero_identificacion' in data:
            cliente.numero_identificacion = data['numero_identificacion']
        
        db.session.commit()
        return cliente_schema.dump(cliente), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Error al actualizar cliente', 'error': str(e)}), 500
    
# -------- Rutas de Préstamos --------
@prestamos_bp.route("/", methods=["POST"])
@manager_or_admin_required
def add_prestamo():
    try:
        data = request.get_json()
        
        libro = Book.query.get_or_404(data.get('libro_id'))
        cliente = Cliente.query.get_or_404(data.get('cliente_id'))
        
        disponibilidad_real = get_real_availability(libro.id)
        
        if disponibilidad_real < 1:
            return jsonify({
                'message': 'No hay ejemplares disponibles de este libro',
                'disponibles': disponibilidad_real
            }), 400
            
        prestamo_activo = Prestamo.query.filter_by(
            cliente_id=cliente.id,
            estado='activo'
        ).first()
        
        if prestamo_activo:
            return jsonify({
                'message': 'El cliente ya tiene un libro prestado',
                'libro': prestamo_activo.libro.titulo
            }), 400
        
        fecha_devolucion = datetime.now() + timedelta(days=7)
        
        new_prestamo = Prestamo(
            libro_id=libro.id,
            cliente_id=cliente.id,
            usuario_id=request.headers.get('X-User-ID'),
            fecha_devolucion_esperada=fecha_devolucion,
            estado='activo'
        )
        
        db.session.add(new_prestamo)
        db.session.commit()
        
        return prestamo_schema.dump(new_prestamo), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Error al registrar préstamo', 'error': str(e)}), 500

@prestamos_bp.route("/<int:prestamo_id>/devolver", methods=["PUT"])
@manager_or_admin_required
def devolver_prestamo(prestamo_id):
    try:
        prestamo = Prestamo.query.get_or_404(prestamo_id)
        
        if prestamo.estado != 'activo':
            return jsonify({'message': 'Este préstamo ya fue devuelto'}), 400
            
        prestamo.fecha_devolucion_real = datetime.now()
        prestamo.estado = 'devuelto'
        
        db.session.commit()
        
        return prestamo_schema.dump(prestamo), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Error al registrar devolución', 'error': str(e)}), 500

@prestamos_bp.route("/", methods=["GET"])
def get_prestamos():
    estado = request.args.get('estado', 'activo')
    prestamos = Prestamo.query.filter_by(estado=estado).all()
    return prestamos_schema.dump(prestamos), 200

# -------- Rutas de Reportes --------
@reportes_bp.route("/prestamos", methods=["GET"])
@admin_required
def get_reportes():
    try:
        search = request.args.get('search', '')
        estado = request.args.get('estado', '')
        
        query = db.session.query(Prestamo).join(Book).join(Cliente).join(User)
        
        if search:
            query = query.filter(
                db.or_(
                    Book.titulo.ilike(f'%{search}%'),
                    Book.autor.ilike(f'%{search}%'),
                    Book.editorial.ilike(f'%{search}%'),
                    Book.isbn.ilike(f'%{search}%'),
                    Cliente.nombre.ilike(f'%{search}%'),
                    Cliente.apellido.ilike(f'%{search}%'),
                    User.username.ilike(f'%{search}%'),
                    db.func.concat(Cliente.nombre, ' ', Cliente.apellido).ilike(f'%{search}%')
                )
            )
            
        if estado:
            query = query.filter(Prestamo.estado == estado)
            
        prestamos = query.all()
        
        return prestamos_schema.dump(prestamos), 200
        
    except Exception as e:
        return jsonify({'message': 'Error al generar reporte', 'error': str(e)}), 500
    
    
@books_bp.route("/<int:book_id>/prestamos-activos", methods=["GET"])
def get_prestamos_activos_libro(book_id):
    try:
        prestamos_activos = Prestamo.query.filter_by(
            libro_id=book_id,
            estado='activo'
        ).all()
        
        return jsonify(prestamos_schema.dump(prestamos_activos)), 200
    except Exception as e:
        return jsonify({'message': 'Error al obtener préstamos activos', 'error': str(e)}), 500