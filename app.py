
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'eternos_secret_key_2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///eternos.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False)
    category = db.Column(db.String(50))
    image_url = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    total_amount = db.Column(db.Float, nullable=False)
    items = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    quantity = db.Column(db.Integer, nullable=False)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    total_amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    items = db.Column(db.Text)
    status = db.Column(db.String(50), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

def export_to_excel():
    users = User.query.all()
    users_data = [{'ID': u.id, 'Username': u.username, 'Email': u.email, 'Role': u.role, 'Created': u.created_at} for u in users]
    df_users = pd.DataFrame(users_data)
    
    products = Product.query.all()
    products_data = [{'ID': p.id, 'Name': p.name, 'Price': p.price, 'Stock': p.stock, 'Category': p.category} for p in products]
    df_products = pd.DataFrame(products_data)
    
    sales = Sale.query.all()
    sales_data = [{'ID': s.id, 'User_ID': s.user_id, 'Total': s.total_amount, 'Items': s.items, 'Date': s.created_at} for s in sales]
    df_sales = pd.DataFrame(sales_data)
    
    orders = Order.query.all()
    orders_data = [{'ID': o.id, 'User_ID': o.user_id, 'Total': o.total_amount, 'Payment': o.payment_method, 'Status': o.status, 'Date': o.created_at} for o in orders]
    df_orders = pd.DataFrame(orders_data)
    
    with pd.ExcelWriter('eternos_data.xlsx') as writer:
        df_users.to_excel(writer, sheet_name='Users', index=False)
        df_products.to_excel(writer, sheet_name='Products', index=False)
        df_sales.to_excel(writer, sheet_name='Sales', index=False)
        df_orders.to_excel(writer, sheet_name='Orders', index=False)

@app.route('/')
def index():
    return render_template('landing.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('shop'))
        else:
            return render_template('login.html', error='Invalid credentials')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            return render_template('register.html', error='Username exists')
        
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, email=email, password=hashed_password, role='customer')
        
        db.session.add(new_user)
        db.session.commit()
        export_to_excel()
        
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/admin/dashboard')
def admin_dashboard():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    return render_template('admin_dashboard.html')

@app.route('/admin/pos')
def admin_pos():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    products = Product.query.all()
    return render_template('admin_pos.html', products=products)

@app.route('/admin/inventory')
def admin_inventory():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    products = Product.query.all()
    return render_template('admin_inventory.html', products=products)

@app.route('/admin/products/add', methods=['POST'])
def add_product():
    if session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    new_product = Product(
        name=data['name'],
        description=data.get('description', ''),
        price=float(data['price']),
        stock=int(data['stock']),
        category=data.get('category', ''),
        image_url=data.get('image_url', '')
    )
    
    db.session.add(new_product)
    db.session.commit()
    export_to_excel()
    
    return jsonify({'success': True, 'product': {'id': new_product.id, 'name': new_product.name, 'price': new_product.price, 'stock': new_product.stock}})

@app.route('/admin/products/update/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    if session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    product = Product.query.get_or_404(product_id)
    data = request.json
    
    product.name = data.get('name', product.name)
    product.description = data.get('description', product.description)
    product.price = float(data.get('price', product.price))
    product.stock = int(data.get('stock', product.stock))
    product.category = data.get('category', product.category)
    product.image_url = data.get('image_url', product.image_url)
    
    db.session.commit()
    export_to_excel()
    
    return jsonify({'success': True})

@app.route('/admin/products/delete/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    if session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    export_to_excel()
    
    return jsonify({'success': True})

@app.route('/admin/sales/create', methods=['POST'])
def create_sale():
    if session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    items = data['items']
    
    for item in items:
        product = Product.query.get(item['product_id'])
        if product and product.stock >= item['quantity']:
            product.stock -= item['quantity']
        else:
            return jsonify({'error': f'Insufficient stock for {product.name}'}), 400
    
    new_sale = Sale(
        user_id=session.get('user_id'),
        total_amount=data['total'],
        items=json.dumps(items)
    )
    
    db.session.add(new_sale)
    db.session.commit()
    export_to_excel()
    
    return jsonify({'success': True, 'sale_id': new_sale.id})

@app.route('/admin/receipt/<int:sale_id>')
def generate_receipt(sale_id):
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    
    sale = Sale.query.get_or_404(sale_id)
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    
    p.setFont("Helvetica-Bold", 20)
    p.drawString(220, 750, "ETERNOS")
    p.setFont("Helvetica", 10)
    p.drawString(200, 730, "Timeless Fashion - Receipt")
    p.line(50, 720, 550, 720)
    
    p.setFont("Helvetica", 12)
    p.drawString(50, 700, f"Sale ID: {sale.id}")
    p.drawString(50, 680, f"Date: {sale.created_at.strftime('%Y-%m-%d %H:%M')}")
    p.line(50, 670, 550, 670)
    
    items = json.loads(sale.items)
    y_position = 650
    
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y_position, "Item")
    p.drawString(300, y_position, "Qty")
    p.drawString(400, y_position, "Price")
    p.drawString(500, y_position, "Total")
    
    y_position -= 20
    p.setFont("Helvetica", 10)
    
    for item in items:
        product = Product.query.get(item['product_id'])
        p.drawString(50, y_position, product.name[:30])
        p.drawString(300, y_position, str(item['quantity']))
        p.drawString(400, y_position, f"${product.price:.2f}")
        p.drawString(500, y_position, f"${product.price * item['quantity']:.2f}")
        y_position -= 20
    
    p.line(50, y_position, 550, y_position)
    y_position -= 20
    
    p.setFont("Helvetica-Bold", 14)
    p.drawString(400, y_position, f"TOTAL: ${sale.total_amount:.2f}")
    
    p.save()
    buffer.seek(0)
    
    return send_file(buffer, as_attachment=True, download_name=f'receipt_{sale_id}.pdf', mimetype='application/pdf')

@app.route('/shop')
def shop():
    products = Product.query.filter(Product.stock > 0).all()
    return render_template('shop.html', products=products)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/cart')
def cart():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    cart_items = db.session.query(Cart, Product).join(Product).filter(Cart.user_id == session['user_id']).all()
    return render_template('cart.html', cart_items=cart_items)

@app.route('/cart/add', methods=['POST'])
def add_to_cart():
    if 'user_id' not in session:
        return jsonify({'error': 'Please login'}), 401
    
    data = request.json
    product_id = data['product_id']
    quantity = data.get('quantity', 1)
    
    cart_item = Cart.query.filter_by(user_id=session['user_id'], product_id=product_id).first()
    
    if cart_item:
        cart_item.quantity += quantity
    else:
        cart_item = Cart(user_id=session['user_id'], product_id=product_id, quantity=quantity)
        db.session.add(cart_item)
    
    db.session.commit()
    return jsonify({'success': True})

@app.route('/cart/remove/<int:cart_id>', methods=['DELETE'])
def remove_from_cart(cart_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    cart_item = Cart.query.get_or_404(cart_id)
    if cart_item.user_id != session['user_id']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    db.session.delete(cart_item)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/checkout', methods=['POST'])
def checkout():
    if 'user_id' not in session:
        return jsonify({'error': 'Please login'}), 401
    
    data = request.json
    payment_method = data.get('payment_method')
    total = data.get('total')
    
    # Get cart items
    cart_items = db.session.query(Cart, Product).join(Product).filter(Cart.user_id == session['user_id']).all()
    
    if not cart_items:
        return jsonify({'error': 'Cart is empty'}), 400
    
    # Create order items list
    order_items = []
    for cart_item, product in cart_items:
        # Check stock
        if product.stock < cart_item.quantity:
            return jsonify({'error': f'Insufficient stock for {product.name}'}), 400
        
        # Reduce stock
        product.stock -= cart_item.quantity
        
        order_items.append({
            'product_id': product.id,
            'product_name': product.name,
            'quantity': cart_item.quantity,
            'price': product.price
        })
    
    # Create order
    new_order = Order(
        user_id=session['user_id'],
        total_amount=total,
        payment_method=payment_method,
        items=json.dumps(order_items),
        status='completed' if payment_method == 'cod' else 'pending'
    )
    
    db.session.add(new_order)
    
    # Clear cart
    Cart.query.filter_by(user_id=session['user_id']).delete()
    
    db.session.commit()
    export_to_excel()
    
    return jsonify({
        'success': True,
        'order_id': new_order.id,
        'payment_method': payment_method
    })

@app.before_request
def create_tables():
    if not hasattr(app, 'db_initialized'):
        db.create_all()
        
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                email='admin@eternos.com',
                password=generate_password_hash('admin123'),
                role='admin'
            )
            db.session.add(admin)
            db.session.commit()
        
        app.db_initialized = True

if __name__ == '__main__':
    app.run(debug=True)
