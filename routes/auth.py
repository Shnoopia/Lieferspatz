from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from db import get_db_connection
from werkzeug.security import check_password_hash

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']  # Email or Username
        password = request.form['password']
        role = request.form['role']

        conn = get_db_connection()
        cursor = conn.cursor()

        if role == 'customer':
            cursor.execute('SELECT * FROM customers WHERE PhoneNumber = ?', (username,))
        else:
            cursor.execute('SELECT * FROM restaurants WHERE Email = ?', (username,))

        user = cursor.fetchone()
        conn.close()

        # if user and check_password_hash(user['Password'], password):
        #     session['user_id'] = user['CustomerID'] if role == 'customer' else user['RestaurantID']
        #     session['role'] = role
        #     session['user'] = dict(user)
        #     flash('Login successful!', 'success')
        #     return redirect(url_for(f'{role}.{role}_dashboard'))
        # else:
        #     flash('Invalid credentials', 'danger')

        if user and check_password_hash(user['Password'], password):
            user_data = dict(user)
            
            # Store the user data separately based on role
            if role == 'customer':
                session['customer'] = user_data  # Store customer data
            else:
                session['restaurant'] = user_data  # Store restaurant data

            session['user_id'] = user_data.get('CustomerID') if role == 'customer' else user_data.get('RestaurantID')
            session['role'] = role
            
            flash('Login successful!', 'success')
            return redirect(url_for(f'{role}.{role}_dashboard'))
        else:
            flash('Invalid credentials', 'danger')


        

    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()  # Clear all session data
    flash('You have logged out successfully!', 'success')
    return redirect(url_for('auth.login'))
