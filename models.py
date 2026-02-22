from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# ----------------------
# USER TABLE
# ----------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    role = db.Column(db.String(20), default="student")


# ----------------------
# MENU TABLE
# ----------------------
class Menu(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    price = db.Column(db.Integer)
    image = db.Column(db.String(200))


# ----------------------
# ORDER TABLE
# ----------------------
class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_name = db.Column(db.String(100))
    item_name = db.Column(db.String(100))
    quantity = db.Column(db.Integer)

    time_slot = db.Column(db.String(50))
    total_price = db.Column(db.Integer)

    payment_method = db.Column(db.String(50))
    payment_status = db.Column(db.String(50), default="Paid")

    status = db.Column(db.String(50), default="Pending")

    timestamp = db.Column(db.DateTime, default=datetime.utcnow)