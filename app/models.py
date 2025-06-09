from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# ---------- Tabla de Roles -------------------
class Role(db.Model):
    __tablename__ = "roles"
    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(255))
    
    def __repr__(self):
        return f"<Role {self.id}: {self.name}>"

# --------- Tabla de Usuarios --------------------------------
class User(db.Model):
    __tablename__ = "users"
    id          = db.Column(db.Integer, primary_key=True)
    username    = db.Column(db.String(50), unique=True, nullable=False)
    password    = db.Column(db.String(255), nullable=False)
    email       = db.Column(db.String(100), unique=True, nullable=False)
    role_id     = db.Column(
        db.Integer,
        db.ForeignKey("roles.id"),
        nullable=False
    )
    created_at  = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp())

    role = db.relationship("Role", backref="users")
    
    def __repr__(self):
        return f"<User: {self.id} {self.username}>"
    
# ---------- Tabla de Libros -------------------
class Book(db.Model):
    __tablename__ = "libros" 
    
    id                  = db.Column(db.Integer, primary_key=True)
    titulo              = db.Column(db.String(255), nullable=False)
    autor               = db.Column(db.String(255), nullable=False)
    editorial           = db.Column(db.String(255))
    anio_publicacion    = db.Column(db.Integer)
    isbn                = db.Column(db.String(13), unique=True, nullable=False)
    cantidad_disponible = db.Column(db.Integer, nullable=False, default=0)
    created_at          = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp())
    
    def __repr__(self):
        return f"<Libro {self.id}: {self.titulo}>"
    
# ---------- Tabla de clientes -------------------
class Cliente(db.Model):
    __tablename__ = "clientes"
    
    id                    = db.Column(db.Integer, primary_key=True)
    nombre                = db.Column(db.String(100), nullable=False)
    apellido              = db.Column(db.String(100), nullable=False)
    correo                = db.Column(db.String(100), nullable=False)
    telefono              = db.Column(db.String(20))
    numero_identificacion = db.Column(db.String(13), unique=True, nullable=False)
    created_at            = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp())
    
    def __repr__(self):
        return f"<Cliente {self.id}: {self.nombre} {self.apellido}>"
    
# ---------- Tabla de prestamos -------------------
class Prestamo(db.Model):
    __tablename__ = "prestamos"
    
    id                        = db.Column(db.Integer, primary_key=True)
    libro_id                  = db.Column(db.Integer, db.ForeignKey("libros.id"), nullable=False)
    cliente_id                = db.Column(db.Integer, db.ForeignKey("clientes.id"), nullable=False)
    usuario_id                = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    fecha_prestamo            = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp())
    fecha_devolucion_esperada = db.Column(db.TIMESTAMP, nullable=False)
    fecha_devolucion_real     = db.Column(db.TIMESTAMP)
    estado                    = db.Column(db.String(20), nullable=False, default="activo")
    
    libro = db.relationship("Book", backref="prestamos")
    cliente = db.relationship("Cliente", backref="prestamos")
    usuario = db.relationship("User", backref="prestamos_registrados")
    
    def __repr__(self):
        return f"<Prestamo {self.id}: Libro {self.libro_id} - Cliente {self.cliente_id}>"