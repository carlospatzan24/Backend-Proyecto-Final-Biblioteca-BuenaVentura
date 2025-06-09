from flask_marshmallow import Marshmallow
from app.models import User, Role, Book, Cliente, Prestamo

ma = Marshmallow()

class RoleSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Role
        load_instance = True
        
role_schema = RoleSchema()
roles_schema = RoleSchema(many=True)

class UserSchema(ma.SQLAlchemyAutoSchema):
    role = ma.Nested(RoleSchema) # pylint: disable=no-member
    
    class Meta:
        model = User
        load_instance = True
        include_fk = True
        exclude = ('password',)
 
user_schema = UserSchema()
users_schema = UserSchema(many=True)

class UserLoginSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = User
        load_instance = True
        include_fk = True

user_login_schema = UserLoginSchema()


class BookSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Book
        load_instance = True
        include_fk = True
        
book_schema = BookSchema()
books_schema = BookSchema(many=True)

class ClienteSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Cliente
        load_instance = True
        include_fk = True
        
cliente_schema = ClienteSchema()
clientes_schema = ClienteSchema(many=True)


class PrestamoSchema(ma.SQLAlchemyAutoSchema):
    libro = ma.Nested(BookSchema) # pylint: disable=no-member
    cliente = ma.Nested(ClienteSchema) # pylint: disable=no-member
    usuario = ma.Nested(UserSchema) # pylint: disable=no-member
    
    class Meta:
        model = Prestamo
        load_instance = True
        include_fk = True
        
prestamo_schema = PrestamoSchema()
prestamos_schema = PrestamoSchema(many=True)