from flask import Blueprint

auth = Blueprint('auth', __name__)

@auth.route('/sign-up')
def login():
    return "SignUp Page"

@auth.route('/POS')
def signup():
    return "Point of Sale Page"

@auth.route('/inventory')
def logout():
    return "Inventory Page"


