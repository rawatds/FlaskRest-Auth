from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_httpauth import HTTPBasicAuth

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///rest.sqlite'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
#app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True

db = SQLAlchemy(app)
ma = Marshmallow(app)
auth = HTTPBasicAuth()

CRED = {'user123' : 'password123'}

@auth.verify_password
def verify(username, passwd):
    if not (username and passwd):
        return False

    return CRED.get(username) == passwd



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


product_schema = ProductSchema()
products_schema = ProductSchema(many=True)


# Routing starts here...

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
# It requires a basic auth

@app.route('/product', methods=['GET'])
@auth.login_required
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






if __name__ == '__main__':
    app.run(debug=True)
