from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_socketio import SocketIO, emit
from models import db, User, Menu, Order
import config
import os
from datetime import date
app = Flask(__name__)

app.config['SECRET_KEY'] = config.SECRET_KEY
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

socketio = SocketIO(app, cors_allowed_origins="*")


# -----------------------
# AUTO INSERT MENU ITEMS
# -----------------------
def insert_menu_items():
    if Menu.query.count() == 0:
        items = [
            ("Burger", 80, "burger.jpg"),
            ("Pizza", 120, "pizza.jpg"),
            ("Samosa", 20, "samosa.jpg"),
            ("Noodles", 90, "noodles.jpg"),
            ("Cold Coffee", 60, "coffee.jpg"),
            ("Sandwich", 70, "sandwich.jpg"),
            ("French Fries", 50, "fries.jpg"),
            ("Momos", 80, "momos.jpg"),
            ("Paneer Roll", 90, "paneer_roll.jpg"),
            ("Chocolate Shake", 75, "chocolate_shake.jpg"),
        ]

        for name, price, image in items:
            db.session.add(Menu(name=name, price=price, image=image))

        db.session.commit()


# -----------------------
# ROUTES
# -----------------------

@app.route("/")
def home():
    return redirect(url_for("login"))


# -----------------------
# SIGNUP
# -----------------------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Email already registered")
            return redirect(url_for("signup"))

        new_user = User(name=name, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()

        flash("Account created successfully")
        return redirect(url_for("login"))

    return render_template("signup.html")


# -----------------------
# LOGIN
# -----------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        # Shopkeeper Login
        if email == config.SHOP_USERNAME and password == config.SHOP_PASSWORD:
            session["role"] = "shop"
            session["name"] = "foodKinzz"
            return redirect(url_for("shop_dashboard"))

        # User Login
        user = User.query.filter_by(email=email, password=password).first()
        if user:
            session["role"] = "user"
            session["name"] = user.name
            return redirect(url_for("user_dashboard"))

        flash("Invalid credentials")
        return redirect(url_for("login"))

    return render_template("login.html")

@app.context_processor
def inject_active_orders():
    if "role" in session and session["role"] == "user":
        user_orders = Order.query.filter_by(
            user_name=session["name"]
        ).all()

        active_count = sum(1 for o in user_orders if o.status != "Completed")

        return dict(active_count=active_count)

    return dict(active_count=0)

# -----------------------
# USER DASHBOARD
# -----------------------
@app.route("/user-dashboard")
def user_dashboard():
    if "role" not in session or session["role"] != "user":
        return redirect(url_for("login"))

    menu_items = Menu.query.all()

    user_orders = Order.query.filter_by(
        user_name=session["name"]
    ).order_by(Order.timestamp.desc()).all()

    active_count = sum(1 for order in user_orders if order.status != "Completed")

    return render_template(
        "student_dashboard.html",
        items=menu_items,
        user_orders=user_orders,
        active_count=active_count
    )

@app.route("/place-order", methods=["POST"])
def place_order():
    if "role" not in session or session["role"] != "user":
        return redirect(url_for("login"))

    item_name = request.form["item_name"]
    quantity = int(request.form["quantity"])
    time_slot = request.form["time_slot"]

    item = Menu.query.filter_by(name=item_name).first()
    total_price = item.price * quantity

    return render_template(
        "payment.html",
        item_name=item_name,
        quantity=quantity,
        time_slot=time_slot,
        total_price=total_price
    )
@app.route("/confirm-payment", methods=["POST"])
def confirm_payment():
    if "role" not in session or session["role"] != "user":
        return redirect(url_for("login"))

    item_name = request.form["item_name"]
    quantity = int(request.form["quantity"])
    time_slot = request.form["time_slot"]
    total_price = int(request.form["total_price"])
    payment_method = request.form["payment_method"]

    new_order = Order(
        user_name=session["name"],
        item_name=item_name,
        quantity=quantity,
        time_slot=time_slot,
        total_price=total_price,
        payment_method=payment_method,
        payment_status="Paid",
        status="Pending"
    )

    db.session.add(new_order)
    db.session.commit()

    # ✅ DEFINE menu_item BEFORE USING IT
    menu_item = Menu.query.filter_by(name=item_name).first()

    socketio.emit("new_order", {
        "id": new_order.id,
        "user_name": session["name"],
        "item_name": item_name,
        "quantity": quantity,
        "time_slot": time_slot,
        "total_price": total_price,
        "payment_status": "Paid",
        "status": "Pending",
        "image": menu_item.image if menu_item else ""
    })

    return render_template("success.html")
@app.route("/update-status", methods=["POST"])
def update_status():
    data = request.get_json()
    order = Order.query.get(data["id"])
    order.status = data["status"]
    db.session.commit()

    socketio.emit("status_updated", {
        "id": order.id,
        "status": order.status
    })

    return {"success": True}
# -----------------------
# SHOP DASHBOARD
# -----------------------

@app.route("/shop-dashboard")
def shop_dashboard():
    if "role" not in session or session["role"] != "shop":
        return redirect(url_for("login"))

    active_orders = Order.query.filter(Order.status != "Completed").all()
    completed_orders = Order.query.filter_by(status="Completed").all()

    # Attach image to each order
    for order in active_orders:
        menu_item = Menu.query.filter_by(name=order.item_name).first()
        order.image = menu_item.image if menu_item else None

    for order in completed_orders:
        menu_item = Menu.query.filter_by(name=order.item_name).first()
        order.image = menu_item.image if menu_item else None

    revenue = sum(order.total_price for order in completed_orders)

    return render_template(
        "shop_dashboard.html",
        active_orders=active_orders,
        completed_orders=completed_orders,
        revenue=revenue
    )
@app.route("/previous-orders")
def previous_orders():
    if "role" not in session or session["role"] != "user":
        return redirect(url_for("login"))

    orders = Order.query.filter_by(user_name=session["name"]).order_by(Order.timestamp.desc()).all()
    return render_template("previous_orders.html", orders=orders)
# -----------------------
# LOGOUT
# -----------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# -----------------------
# RUN APP
# -----------------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        insert_menu_items()

    socketio.run(app, debug=True)