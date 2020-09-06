from flask import Flask, request, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
import uuid, jwt
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import  datetime, timedelta
from functools import wraps

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///rest-jwt.sqlite'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'MySecretKe4'

db = SQLAlchemy(app)
ma = Marshmallow(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(50), unique=True)
    name = db.Column(db.String(50), nullable=False)
    password = db.Column(db.String(80))
    user_type = db.Column(db.String(10))

    def __init__(self, name, password, uuid, user_type):
        self.name = name
        self.password = password
        self.uuid = uuid
        self.user_type = user_type

    def __repr__(self):
        return f"User({self.name}, {self.user_type}, {self.id})"

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    desc = db.Column(db.String(100))
    price = db.Column(db.Float)
    qty = db.Column(db.Integer)

    def __init__(self, name, desc, price, qty):
        self.name = name
        self.desc = desc
        self.price = price
        self.qty = qty

class ProductSchema(ma.Schema):
    class Meta:
        fields = ('id', 'name', 'desc', 'price', 'qty')

class UserSchema(ma.Schema):
    class Meta:
        fields = ('id', 'name', 'password', 'uuid', 'user_type')


product_schema = ProductSchema()
products_schema = ProductSchema(many=True)

user_schema = UserSchema()
users_schema = UserSchema(many=True)


# Auth related stuff here.. - decorator
# e.g. preauthorize(['admin']) - Like we have in Java Spring Security
# or   preauthorize(['admin', 'user'])
# The user has to pass the token in the header 'x-dsr-token'

def preauthorize(user_types_list):
    def login_decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            token = None

            if 'x-dsr-token' in request.headers:
                token = request.headers['x-dsr-token']

            if not token:
                return jsonify({'message': 'Missing token value!'}), 401

            # If token found, lets decode it and get the info inside it
            try:
                data = jwt.decode(token, app.config['SECRET_KEY'])
                current_user = User.query.filter_by(uuid = data['uuid']).first()
                user_type = data['user_type']
                #print("** Token has: ", current_user, user_type, user_types_list)
                if not user_type in user_types_list:
                    return jsonify({'message': 'You are not authorize access this URL!'}), 401
            except Exception as ex:
                print(ex)
                return jsonify({'message': 'Error in accessing the token: ' + str(ex)}), 401
            return f(*args, **kwargs)
        return wrapper
    return login_decorator

# Routing starts here...
# Add a user

@app.route('/user', methods=['POST'])
def add_user():
    """
        {
            "name" : "dsrawat",
            "password" : "12345",
            "user_type" : "admin"
        }
   """
    print("**", request.get_json(), request.json)
    name = request.json['name']
    plain_pass = request.json['password']
    user_type = request.json['user_type']

    hash_pw = generate_password_hash(plain_pass, method="sha256")

    user = User(name, hash_pw, str(uuid.uuid4()), user_type)
    db.session.add(user)
    db.session.commit()

    return user_schema.jsonify(user)

# List all users

@app.route('/user', methods=['GET'])
@preauthorize(['user', 'admin'])
def list_users():
    users = User.query.all()
    result = users_schema.dump(users)
    return jsonify(result)

# List one user
@app.route('/user/<uuid>', methods=['GET'])
def list_user(uuid):
    users = User.query.filter_by(uuid=uuid).first()
    return jsonify(users)


# Add a product
@app.route('/product', methods=['POST'])
def add_product():
    name = request.json['name']
    desc = request.json['desc']
    price = request.json['price']
    qty = request.json['qty']

    product = Product(name, desc, price, qty)
    db.session.add(product)
    db.session.commit()

    return product_schema.jsonify(product)



# List all products
@app.route('/product', methods=['GET'])
def list_products():
    products = Product.query.all()
    result = products_schema.dump(products)
    #print(dir(jsonify()))
    return jsonify(result)

    # OR
    #return jsonify(products_schema.dump(products))

# List a proudct
@app.route('/product/<id>', methods=['GET'])
def get_product(id):
    product = Product.query.get(id)
    return product_schema.jsonify(product)


# UPDATE a proudct
@app.route('/product/<id>', methods=['PUT'])
def update_product(id):

    product = Product.query.get(id)

    # print(request)
    # print(request.json)
    # print('name' in request.json)
    # print('price' in request.json)

    if 'name' in  request.json: product.name = request.json['name']
    if 'desc' in request.json: product.desc = request.json['desc']
    if 'price' in request.json: product.price = request.json['price']
    if 'qty' in request.json: product.qty = request.json['qty']

    db.session.commit()
    return product_schema.jsonify(product)

# Delete a proudct
@app.route('/product/<id>', methods=['DELETE'])
def delete_product(id):
    product = Product.query.get(id)
    db.session.delete(product)
    db.session.commit()
    return product_schema.jsonify(product)


# Login route - provide username and password - it will return a jwt token with some expiry
@app.route('/login', methods=['POST'])
def login():
    auth = request.authorization
    #print(auth, auth.username, auth.password)

    if not auth or not auth.username or not auth.password:
        #return jsonify({'msg' : 'ok'}), 401
        return make_response({'message' : 'Auth token is missing or invalid'}, 401, {'WWW-authentication' : 'Basic realm=\'Login required!\''})

    user = User.query.filter_by(name = auth.username).first()
    if not user:
        return make_response({'message': 'Invalid user'}, 401)

    if check_password_hash(user.password, auth.password):
        token = jwt.encode({'uuid': user.uuid, 'user_type' : user.user_type, 'exp' : datetime.utcnow() + timedelta(minutes=2)}, app.config['SECRET_KEY'])
        return jsonify({'token' : token.decode('UTF-8')})

    return make_response({'message': 'User cannot be verified'}, 401)


if __name__ == '__main__':
    app.run(debug=True)
