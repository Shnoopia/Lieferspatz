from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from db import get_db_connection
from werkzeug.security import generate_password_hash
from datetime import datetime
from werkzeug.utils import secure_filename
import os
from utils import allowed_file
from config import Config
import RDB_util

restaurant_bp = Blueprint('restaurant', __name__)

@restaurant_bp.route('/register/restaurant', methods=['GET', 'POST'])
def register_restaurant():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']  # Unique email for login
        address = request.form['address']
        zip_code = request.form['zip_code']
        description = request.form['description']
        image = request.files['image_url']
        password = generate_password_hash(request.form['password'])
        open_time = request.form['open_time']
        close_time = request.form['close_time']
        delivery_zip_codes = request.form.getlist('delivery_zip_codes') # Get a list of delivery zip codes

         # Validate ZIP code
        if not zip_code.isdigit():
            flash('Please provide a valid ZIP Code', 'danger')
            return render_template('register_restaurant.html')

        # Validate delivery ZIP codes
        for delivery_zip_code in delivery_zip_codes:
            if not delivery_zip_code.isdigit():
                flash('All delivery ZIP codes must be valid', 'danger')
                return render_template('register_restaurant.html')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM restaurants WHERE Email = ?', (email,))
        existing_restaurant = cursor.fetchone()

        if existing_restaurant:
            flash('Email is already in use, please choose a different one.', 'danger')
            conn.close()
            return render_template('register_restaurant.html')
        
        if image and not allowed_file(image.filename):
            flash('Please use .jpg or .jpeg or .png or .gif extension images only', 'danger')
            return render_template('register_restaurant.html')

        image_path = None
        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            image_path = os.path.join(Config.UPLOAD_FOLDER, filename)
            os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
            image.save(image_path)
            image_path = image_path.replace(os.path.sep,'/')

        relative_image_path = image_path if image_path else None
        
        # Insert new restaurant into the database only if the username is unique - USE cursor here instead of conn
        cursor.execute('''
            INSERT INTO restaurants (Name, Email, Address, ZipCode, Description, ImageURL, Password, OpenTime, CloseTime, CreatedAt)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, email, address, zip_code, description, relative_image_path, password, open_time, close_time, datetime.now()))

        restaurant_id = cursor.lastrowid # Gets the RestaurantID of the latest created restaurant

        for zip_code in delivery_zip_codes:
            cursor.execute('''
                INSERT INTO delivery_zip_codes (RestaurantID, ZipCode)
                VALUES (?, ?)
            ''', (restaurant_id, zip_code))

        conn.commit()
        conn.close()

        flash('Restaurant registration successful!', 'success')
        return redirect(url_for('auth.login'))
    return render_template('register_restaurant.html')

@restaurant_bp.route('/restaurant/dashboard')
def restaurant_dashboard():
    # Check if restaurant data exists in session
    if 'restaurant' not in session:
        return redirect(url_for('auth.login'))
    
    # Get the latest restaurant data from the database
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM restaurants WHERE RestaurantID = ?', (session['restaurant']['RestaurantID'],))
    restaurant_data = cursor.fetchone()
    
     # Fetch delivery ZIP codes
    cursor.execute('SELECT ZipCode FROM delivery_zip_codes WHERE RestaurantID = ?', (session['restaurant']['RestaurantID'],))
    delivery_zip_codes = [row['ZipCode'] for row in cursor.fetchall()]
        
    conn.close()
    
    # Update the session with the latest restaurant data
    session['restaurant'] = dict(restaurant_data)

    # Determine the current status of the restaurant
    current_time = datetime.now().time()
    open_time = datetime.strptime(restaurant_data['OpenTime'], '%H:%M').time()
    close_time = datetime.strptime(restaurant_data['CloseTime'], '%H:%M').time()
    
    if open_time < close_time:
        is_open = open_time <= current_time < close_time
    else:
        is_open = current_time >= open_time or current_time < close_time
    
    status = "OPEN" if is_open else "CLOSED"

    #Get items from Database and display
    rows = RDB_util.get_all_items_from_database()

    # Convert CreatedAt to datetime object
    items = []
    for row in rows:
        row = list(row)  # Convert tuple to list to allow modification
        row[4] = datetime.strptime(row[4], '%Y-%m-%d %H:%M:%S.%f')
        items.append(row)

    # Access restaurant session data
    restaurant_data = session['restaurant']
    return render_template('dashboard_restaurant.html', user=restaurant_data, items = items, delivery_zip_codes=delivery_zip_codes, status=status)


@restaurant_bp.route('/restaurant/additems', methods=['GET', 'POST'])
def restaurant_additems():
    if request.method == 'POST':

        image = request.files['image_url']

        # Checking whether the image extension is not allowed then display a flash message
        if image and not allowed_file(image.filename):
            flash('Please use .jpg or .jpeg or .png or .gif extension images only', 'danger')
            return render_template('add_item.html', user=session['restaurant'])
        
        # Validate price
        try:
            price = float(request.form['Price'])
        except ValueError:
            flash('Price must be a number', 'danger')
            return render_template('add_item.html', user=session['restaurant'])
        
        image_path = None
        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            image_path = os.path.join(Config.UPLOAD_FOLDER, filename)
            os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
            image.save(image_path)
            image_path = image_path.replace(os.path.sep,'/')

        relative_image_path = image_path if image_path else None

        category = request.form['Category']

        RDB_util.add_item_to_database(request.form['Name'], request.form['Price'], request.form['Description'], relative_image_path, category)
        flash('Item Added!', 'success')

    restaurant_data = session['restaurant']
    return render_template('add_item.html', user=restaurant_data)

# @restaurant_bp.route('/delete_item', methods=['GET', 'POST'])
# def restaurant_delete_item():
#     RDB_util.delete_item_from_database(request.form['ItemID'])
#     return redirect(url_for('restaurant.restaurant_dashboard'))

@restaurant_bp.route('/edit_item_screen', methods=['GET', 'POST'])
def restaurant_edit_item_screen():
    # clicking edit on html page retrieves the ItemID and then renders the edit item page
    # we require 2 pages because I want to first display old data and then submit new data
    item_id = request.args.get('ItemID') if request.method == 'GET' else request.form['ItemID']
    row = RDB_util.get_item_from_database(item_id)
    restaurant_data = session['restaurant']
    return render_template('edit_item.html', user=restaurant_data, item=row)

@restaurant_bp.route('/edit_item', methods=['GET', 'POST'])
def restaurant_edit_item():
    conn = RDB_util.connect_to_database()
    #update items
    if request.method == 'POST':

        image = request.files['image_url']
        row = RDB_util.get_item_from_database(request.form['ItemID'])
        existing_image_path = row[0][5]  # Assuming the image URL is at index 5


       # Checking whether the image extension is not allowed then display a flash message
        if image and not allowed_file(image.filename):
            flash('Please use .jpg or .jpeg or .png or .gif extension images only', 'danger')
            row = RDB_util.get_item_from_database(request.form['ItemID'])
            restaurant_data = session['restaurant']
            return render_template('edit_item.html', user=restaurant_data, item=row)
        
        # Validate price
        try:
            price = float(request.form['Price'])
        except ValueError:
            flash('Price must be a number', 'danger')
            row = RDB_util.get_item_from_database(request.form['ItemID'])
            restaurant_data = session['restaurant']
            return render_template('edit_item.html', user=restaurant_data, item=row)

        image_path = None
        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            image_path = os.path.join(Config.UPLOAD_FOLDER, filename)
            os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
            image.save(image_path)
            image_path = image_path.replace(os.path.sep,'/')
        else:
            image_path = existing_image_path

        relative_image_path = image_path if image_path else None
        RDB_util.update_item_to_database(request.form['Name'], request.form['Price'], request.form['Description'], relative_image_path, request.form['ItemID'])
        flash('Item Edited!', 'success')

    return redirect(url_for('restaurant.restaurant_dashboard'))



@restaurant_bp.route('/restaurant/received_orders')
def received_orders():
    if 'restaurant' not in session:
        return redirect(url_for('auth.login'))
    # Seperate Both (InProcess, InDelivery) AND (Completed, Rejected) To Two Segments For Ordering.
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT o.OrderID, c.FirstName || ' ' || c.LastName AS CustomerName, c.Address, o.CreatedAt, o.Notes, o.TotalPrice, o.Status
        FROM Orders o
        JOIN customers c ON o.CustomerID = c.CustomerID
        WHERE o.RestaurantID = ? AND o.Status IN (?, ?)
        ORDER BY o.OrderID DESC
    ''', (session['restaurant']['RestaurantID'], 'InProcess', 'InDelivery',))
    currentorders = cursor.fetchall()

    cursor.execute('''
        SELECT o.OrderID, c.FirstName || ' ' || c.LastName AS CustomerName, c.Address, o.CreatedAt, o.Notes, o.TotalPrice, o.Status
        FROM Orders o
        JOIN customers c ON o.CustomerID = c.CustomerID
        WHERE o.RestaurantID = ? AND o.Status = ?
        ORDER BY o.OrderID DESC
    ''', (session['restaurant']['RestaurantID'], 'Completed',))
    completedorders = cursor.fetchall()
    
    cursor.execute('''
        SELECT o.OrderID, c.FirstName || ' ' || c.LastName AS CustomerName, c.Address, o.CreatedAt, o.Notes, o.TotalPrice, o.Status
        FROM Orders o
        JOIN customers c ON o.CustomerID = c.CustomerID
        WHERE o.RestaurantID = ? AND o.Status = ?
        ORDER BY o.OrderID DESC
    ''', (session['restaurant']['RestaurantID'], 'Rejected',))
    rejectedorders = cursor.fetchall()

   # Convert sqlite3.Row objects to dictionaries
    currentorders = [dict(order) for order in currentorders]
    for order in currentorders:
        order['CreatedAt'] = datetime.strptime(order['CreatedAt'], '%Y-%m-%d %H:%M:%S.%f')

    completedorders = [dict(order) for order in completedorders]
    for order in completedorders:
        order['CreatedAt'] = datetime.strptime(order['CreatedAt'], '%Y-%m-%d %H:%M:%S.%f')

    rejectedorders = [dict(order) for order in rejectedorders]
    for order in rejectedorders:
        order['CreatedAt'] = datetime.strptime(order['CreatedAt'], '%Y-%m-%d %H:%M:%S.%f')

    # Fetch items for each order
    for order in currentorders:
        cursor.execute('''
            SELECT i.Name, oi.Quantity
            FROM OrderItems oi
            JOIN items i ON oi.ItemID = i.ItemID
            WHERE oi.OrderID = ?
        ''', (order['OrderID'],))
        order['Items'] = cursor.fetchall()

    for order2 in completedorders:
        cursor.execute('''
            SELECT i.Name, oi.Quantity
            FROM OrderItems oi
            JOIN items i ON oi.ItemID = i.ItemID
            WHERE oi.OrderID = ?
        ''', (order2['OrderID'],))
        order2['Items'] = cursor.fetchall()

    for order3 in rejectedorders:
        cursor.execute('''
            SELECT i.Name, oi.Quantity
            FROM OrderItems oi
            JOIN items i ON oi.ItemID = i.ItemID
            WHERE oi.OrderID = ?
        ''', (order3['OrderID'],))
        order3['Items'] = cursor.fetchall()

    conn.close()

    restaurant_data = session['restaurant']
    return render_template('received_orders.html', completedorders=completedorders, currentorders=currentorders, rejectedorders=rejectedorders, user=restaurant_data)

@restaurant_bp.route('/restaurant/update_order_status/<int:order_id>', methods=['POST'])
def update_order_status(order_id):
    if 'restaurant' not in session:
        return redirect(url_for('auth.login'))
    
    new_status = request.form['status']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE Orders SET Status = ? WHERE OrderID = ?', (new_status, order_id))
    conn.commit()
    conn.close()
    flash(f"Order {order_id} is {new_status.lower()}.", 'success')
    return redirect(url_for('restaurant.received_orders'))

@restaurant_bp.route('/restaurant/edit', methods=['GET', 'POST'])
def edit_restaurant():
    if 'restaurant' not in session:
        return redirect(url_for('auth.login'))

    restaurant_data = session['restaurant']
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        address = request.form['address']
        zip_code = request.form['zip_code']
        description = request.form['description']
        open_time = request.form['open_time']
        close_time = request.form['close_time']
        delivery_zip_codes = request.form.getlist('delivery_zip_codes')

        # Validate ZIP code
        if not zip_code.isdigit():
            flash('Please provide a valid ZIP Code', 'danger')
            return render_template('edit_restaurant.html', restaurant=restaurant_data, delivery_zip_codes=delivery_zip_codes, user=restaurant_data)

        # Validate delivery ZIP codes
        for delivery_zip_code in delivery_zip_codes:
            if not delivery_zip_code.isdigit():
                flash('All delivery ZIP codes must be valid', 'danger')
                return render_template('edit_restaurant.html', restaurant=restaurant_data, delivery_zip_codes=delivery_zip_codes, user=restaurant_data)

        # for delivery_zip_code in delivery_zip_codes:
        #     if not delivery_zip_code.isdigit() or not delivery_zip_code:
        #         flash('All delivery ZIP codes must be valid and not empty', 'danger')
        #         return render_template('edit_restaurant.html', restaurant=restaurant_data, delivery_zip_codes=delivery_zip_codes, user=restaurant_data)


        image = request.files['image_url']
        image_path = restaurant_data['ImageURL']

        if image and not allowed_file(image.filename):
            flash('Please use .jpg, .jpeg, .png, or .gif extension images only', 'danger')
            return render_template('edit_restaurant.html', restaurant=restaurant_data, delivery_zip_codes=delivery_zip_codes)

        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            image_path = os.path.join(Config.UPLOAD_FOLDER, filename)
            os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
            image.save(image_path)
            image_path = image_path.replace(os.path.sep, '/')

        cursor.execute('''
            UPDATE restaurants
            SET Name = ?, Address = ?, ZipCode = ?, Description = ?, ImageURL = ?, OpenTime = ?, CloseTime = ?
            WHERE RestaurantID = ?
        ''', (name, address, zip_code, description, image_path, open_time, close_time, restaurant_data['RestaurantID']))

        cursor.execute('DELETE FROM delivery_zip_codes WHERE RestaurantID = ?', (restaurant_data['RestaurantID'],))
        for zip_code in delivery_zip_codes:
            cursor.execute('''
                INSERT INTO delivery_zip_codes (RestaurantID, ZipCode)
                VALUES (?, ?)
            ''', (restaurant_data['RestaurantID'], zip_code))

        conn.commit()
        conn.close()

        flash('Restaurant details updated successfully!', 'success')
        return redirect(url_for('restaurant.restaurant_dashboard'))

    cursor.execute('SELECT ZipCode FROM delivery_zip_codes WHERE RestaurantID = ?', (restaurant_data['RestaurantID'],))
    delivery_zip_codes = [row['ZipCode'] for row in cursor.fetchall()]
    conn.close()
    restaurant_data = session['restaurant']
    return render_template('edit_restaurant.html', restaurant=restaurant_data, delivery_zip_codes=delivery_zip_codes, user=restaurant_data )

@restaurant_bp.route('/delete_item', methods=['POST'])
def restaurant_delete_item():
    item_id = request.form['ItemID']
    RDB_util.delete_item_from_database(item_id)
    flash('Item Deleted!', 'success')
    return redirect(url_for('restaurant.restaurant_dashboard'))
