from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from db import get_db_connection
from werkzeug.security import generate_password_hash
from datetime import datetime
import sqlite3

customer_bp = Blueprint('customer', __name__)

def array_merge( first_array, second_array ):
    if isinstance(first_array, list) and isinstance(second_array, list): # Joining ORDERED Lists
        return first_array + second_array
    elif isinstance(first_array, dict) and isinstance(second_array, dict): # Joining Dictionaries Without Dupe Keys.
        return dict(list(first_array.items()) + list(second_array.items() ))
    elif isinstance(first_array, set) and isinstance(second_array, set): # Joining UNORDERED NON-DUPE Sets
        return first_array.union(second_array)
    return False

@customer_bp.route('/register/customer', methods=['GET', 'POST'])
def register_customer():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        address = request.form['address']
        zip_code = request.form['zip_code']
        phone_number = request.form['phone_number']
        password = generate_password_hash(request.form['password'])

        # Validate ZIP code and phone number
        if not zip_code.isdigit():
            flash('Please provide a valid ZIP Code', 'danger')
            return render_template('register_customer.html')
        
        if not phone_number.isdigit():
            flash('Please provide a valid phone number', 'danger')
            return render_template('register_customer.html')

        conn = get_db_connection()

        cursor = conn.cursor()
        cursor.execute('SELECT 1 FROM customers WHERE PhoneNumber = ?', (phone_number,))
        existing_customer = cursor.fetchone()

        if existing_customer:
            flash('Phone Number is already in use, please choose a different one.', 'danger')
            conn.close()
            return render_template('register_customer.html')
        
        cursor.execute('''
            INSERT INTO customers (FirstName, LastName, Address, ZipCode, PhoneNumber, Password, CreatedAt)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (first_name, last_name, address, zip_code, phone_number, password, datetime.now()))
        conn.commit()
        conn.close()

        flash('Customer registration successful!', 'success')
        return redirect(url_for('auth.login'))
    return render_template('register_customer.html')

@customer_bp.route('/customer/dashboard')
def customer_dashboard():
    if 'customer' not in session:
        return redirect(url_for('auth.login'))
    # Force Customer To Empty Cart Instead of Clicking To Dashboard.
    if 'shoppingcart' in session:
        flash('You May Only Choose One Restaurant To Order From, Empty Shopping Cart First.', 'danger')
        return redirect(url_for('customer.itemorder'))
    conn = get_db_connection()
    cursor = conn.cursor()

    # Access customer session data
    customer_data = session['customer']

    cursor.execute('SELECT * FROM restaurants WHERE RestaurantID IN (SELECT RestaurantID FROM delivery_zip_codes WHERE ZipCode = ?)', (customer_data['ZipCode'],))
    restaurantsclose = cursor.fetchall()
    conn.close()
    return render_template('dashboard_customer.html', user=customer_data, restaurantsclose=restaurantsclose)

@customer_bp.route('/customer/itemorder', methods=['GET', 'POST'])
def itemorder():
    if 'customer' not in session:
        return redirect(url_for('auth.login'))
    if request.method == 'POST': # Did Not Add In Cart Anything Yet
        customer_data = session['customer']
        user_id = customer_data['CustomerID']
        conn = get_db_connection()
        cursor = conn.cursor()
        
        chosenID = request.form['selectedID'] # Receiving the ID From Clicking Restaurant Image/Alt.
        session['chosenrestID'] = chosenID  # Update the session with the new chosen restaurant ID
        cursor.execute('SELECT * FROM restaurants WHERE RestaurantID = ?', (chosenID,)) 
        truerestaurantchosen = cursor.fetchone()

        # cursor.execute('SELECT * FROM Items WHERE RestaurantID = ?', (chosenID,)) 
        cursor.execute('SELECT * FROM Items WHERE RestaurantID = ? ORDER BY Category, Name', (chosenID,))
        trueitemschosen = cursor.fetchall()
        return render_template('itemorder.html', user=customer_data, itemschosen=trueitemschosen, restaurantchosen=truerestaurantchosen)

    if session.get('chosenrestID'):   
        conn = get_db_connection()
        cursor = conn.cursor()
        customer_data = session['customer']
        savedID = session['chosenrestID']
        cursor.execute('SELECT * FROM restaurants WHERE RestaurantID = ?', (savedID,))
        truerestaurantchosen = cursor.fetchone()
        # cursor.execute('SELECT * FROM Items WHERE RestaurantID = ?', (savedID,))
        cursor.execute('SELECT * FROM Items WHERE RestaurantID = ? ORDER BY Category, Name', (savedID,))
        trueitemschosen = cursor.fetchall()
        return render_template('itemorder.html', user=customer_data, itemschosen=trueitemschosen, restaurantchosen=truerestaurantchosen)

@customer_bp.route('/customer/addtocart', methods=['GET', 'POST'])
def addtocart():
    if 'customer' not in session:
        return redirect(url_for('auth.login'))
    if request.method == 'POST':
        # Insert (OR REPLACE) Into OrderItems Table New Food, With Amount, Refresh Again Upon Changing -/+.
        quantity = int(request.form['productquantity'])
        itemtoadd = int(request.form['chosenItemID'])
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM Items WHERE ItemID = ?', (itemtoadd,))
        itemrow = cursor.fetchone()
        itemDict = { str(itemrow['ItemID']) : {'Name' : itemrow['Name'], 'ItemToAdd' : itemrow['ItemID'], 'Quantity' : quantity, 'Price' : itemrow['Price'], 'TotalPrice' : itemrow['Price']*quantity } }
        total_price = 0
        total_quantity = 0
        session.modified = True

        if 'shoppingcart' in session: # If The Cart Has Any Items, Append, Or Create One.
            if itemrow['ItemID'] in session['shoppingcart']: # Somewhere in Cart, Find It and Update.
                for key, value in session['shoppingcart'].items(): 
            # IMPORTANT!! .items is a Built-In Function To Return Dictionary View.
                    if itemrow['ItemID'] == key:
                        oldquantity = session['shoppingcart'][key]['Quantity']
                        total_quantity = oldquantity + quantity
                        session['shoppingcart'][key]['Quantity'] = total_quantity
                        session['shoppingcart'][key]['TotalPrice'] = total_quantity * itemDict['Price']
            else:
                session['shoppingcart'] = array_merge(session['shoppingcart'], itemDict)

            for key, value in session['shoppingcart'].items(): # Updating Shopping Cart Item.
                singlequantity = int(session['shoppingcart'][key]['Quantity'])
                singleprice = float(session['shoppingcart'][key]['TotalPrice'])
                total_price += singleprice
                total_quantity += singlequantity

        else: # Create New Shopping Cart
            session['shoppingcart'] = itemDict
            total_price += quantity * itemrow['Price']
            total_quantity += quantity

        session['total_quantity'] = total_quantity
        session['total_price'] = total_price
        print(session) # For Debugging.
        conn.close()
        return redirect(url_for('customer.itemorder'))
    
    # Returns Back To Item Displaying, With The Updated Cart.
@customer_bp.route('/customer/empty')
def empty_cart():
    if 'shoppingcart' in session:
        session.pop('shoppingcart')
        session['total_price'] = 0
        session['total_quantity'] = 0
    return redirect(url_for('customer.itemorder'))

@customer_bp.route('/customer/deleteproduct', methods=['GET', 'POST'])
def deleteproduct():
    if request.method == 'POST':
        itemtodelete = request.form['deleteItemID']
        totalprice = 0
        totalquantity = 0
        session.modified = True

        for item in session['shoppingcart'].items(): # Searching Item to Delete First.
            if item[0] == itemtodelete: # (Initial Coincidence)
                session['shoppingcart'].pop(item[0], None)
                if 'shoppingcart' in session: # In The First Place, Update on Del.
                    for key, value in session['shoppingcart'].items():
                        singlequantity = session['shoppingcart'][key]['Quantity']
                        singleprice = session['shoppingcart'][key]['TotalPrice']
                        totalprice += singleprice
                        totalquantity += singlequantity
                break # Cart is Empty After First Deletion.
        if totalquantity == 0:
            session.pop('shoppingcart') # Deleting Shopping Cart Entirely on 1-Item Del.
        else:
            session['total_price'] = totalprice
            session['total_quantity'] = totalquantity

    return redirect(url_for('customer.itemorder'))

@customer_bp.route('/customer/paymentconfirm', methods=['GET', 'POST'])
def paymentconfirm():
    if 'customer' not in session:
        return redirect(url_for('auth.login'))
    if 'shoppingcart' not in session:
        return redirect(url_for('customer.customer_dashboard'))
    
    customer_data = session['customer']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM restaurants WHERE RestaurantID = ?', (session['chosenrestID'],))
    restaurantchosen = cursor.fetchone()
    conn.close()
 
    return render_template('paymentconfirm.html', customer=customer_data, restaurantchosen=restaurantchosen)

@customer_bp.route('/customer/editcustomerdetails', methods=['GET', 'POST'])
def editcustomerdetails():
    if 'customer' not in session:
        return redirect(url_for('auth.login'))
    # Get user details (if needed)
    customer_data = session['customer']

    if request.method == 'POST':
        user_id = customer_data['CustomerID']
        conn = get_db_connection()
        cursor = conn.cursor()

        first_name = request.form['first_name']
        last_name = request.form['last_name']
        address = request.form['address']
        zip_code = request.form['zip_code']

        # Validate ZIP code
        if not zip_code.isdigit():
            flash('Please provide a valid ZIP Code', 'danger')
            return render_template('editcustomerdetails.html', user=customer_data)

        datachange = ' UPDATE customers SET FirstName=?, LastName=?, Address=?, ZipCode=? WHERE CustomerID = ? '
        cursor.execute(datachange, (first_name, last_name, address, zip_code, user_id))
        conn.commit()
        cursor.execute('SELECT * FROM customers WHERE CustomerID = ?', (user_id,))
        session['customer'] = dict(cursor.fetchone())
        conn.close()
        
        flash('Customer Details updated successfully!', 'success')
        return redirect(url_for('customer.customer_dashboard'))
    return render_template('editcustomerdetails.html', user=session['customer'])

# Ensure That Shopping Cart Refuses Customer Choosing Another Rest, Flash Too.

@customer_bp.route('/customer/handle_payment/<action>', methods=['GET', 'POST'])
def handle_payment(action):
    if 'customer' not in session:
        return redirect(url_for('auth.login'))
    
    customer_data = session['customer']
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check Balance First.
    cursor.execute('SELECT Balance FROM customers WHERE CustomerID = ?', (customer_data['CustomerID'],))
    balance = cursor.fetchone()
    if action == 'invalid':
        flash("Insufficient Balance Amount.", 'danger')
        session.pop('shoppingcart')
        session['total_price'] = 0
        session['total_quantity'] = 0
        conn.close()
        return redirect(url_for('customer.customer_dashboard'))
    else:
        NotesToAdd = request.form.get('notestoadd', '')
        status = 'InProcess' if action == 'accept' else 'Rejected'
        
        # Calculate RestaurantMoney and LieferMoney only if the action is 'accept'
        restaurant_money = 0.00
        liefer_money = 0.00
        if action == 'accept':
            total_price = session['total_price']
            restaurant_money = round(total_price * 0.85, 2)
            liefer_money = round(total_price * 0.15, 2)
        
        # Insert Order
        cursor.execute('''
            INSERT INTO Orders (CustomerID, RestaurantID, Notes, TotalPrice, Status, CreatedAt, RestaurantMoney, LieferMoney)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (customer_data['CustomerID'], session['chosenrestID'], NotesToAdd, session['total_price'], status, datetime.now(), restaurant_money, liefer_money))
        OrderID = cursor.lastrowid
        
        # Insert Order Items
        for key, value in session['shoppingcart'].items():
            itemID = session['shoppingcart'][key]['ItemToAdd']  # Or = "key"
            quantity = session['shoppingcart'][key]['Quantity']
            priceofitem = session['shoppingcart'][key]['Price']
            cursor.execute('INSERT INTO OrderItems (OrderID, ItemID, Quantity, Price) VALUES (?, ?, ?, ?)', 
                           (OrderID, itemID, quantity, priceofitem))
        
        if action == 'accept':
            newbalance = balance[0] - session['total_price']
            cursor.execute('UPDATE customers SET Balance = ? WHERE CustomerID = ?', (newbalance, customer_data['CustomerID']))
            session['customer']['Balance'] = newbalance  # Update the balance in the session
            
            # Update restaurant's balance
            cursor.execute('SELECT Balance FROM restaurants WHERE RestaurantID = ?', (session['chosenrestID'],))
            restaurant_balance = cursor.fetchone()[0]
            new_restaurant_balance = restaurant_balance + restaurant_money
            cursor.execute('UPDATE restaurants SET Balance = ? WHERE RestaurantID = ?', (new_restaurant_balance, session['chosenrestID']))
            
            # # Import socketio here to avoid circular import FOR FUTURE => CURRENTLY NOT WORKING
            # from app import socketio
            # # Emit WebSocket event to update restaurant balance
            # socketio.emit('update_balance', {'restaurant_id': session['chosenrestID'], 'new_balance': new_restaurant_balance}, room=f'restaurant_{session["chosenrestID"]}')
        
        conn.commit()
        conn.close()
        
        if action == 'accept':
            flash("Payment Accepted and Successful.", 'success')
        else:
            flash("Payment Declined by Restaurant.", 'danger')
        
        # Clear cart
        session.pop('shoppingcart', None)
        session['total_price'] = 0
        session['total_quantity'] = 0
        return redirect(url_for('customer.customer_dashboard'))

@customer_bp.route('/customer/past_orders')
def past_orders():
    if 'customer' not in session:
        return redirect(url_for('auth.login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT o.OrderID, r.Name, r.Address, o.CreatedAt, o.Notes, o.TotalPrice, o.Status
        FROM Orders o
        JOIN customers c ON c.CustomerID = o.CustomerID
        JOIN restaurants r ON r.RestaurantID = o.RestaurantID
        WHERE o.CustomerID = ? AND o.Status IN (?, ?)
        ORDER BY o.OrderID DESC
    ''', (session['customer']['CustomerID'], 'InProcess', 'InDelivery',))
    currentorders = cursor.fetchall()

    cursor.execute('''
        SELECT o.OrderID, r.Name, r.Address, o.CreatedAt, o.Notes, o.TotalPrice, o.Status
        FROM Orders o
        JOIN customers c ON c.CustomerID = o.CustomerID
        JOIN restaurants r ON r.RestaurantID = o.RestaurantID
        WHERE o.CustomerID = ? AND o.Status IN (?, ?)
        ORDER BY o.OrderID DESC
    ''', (session['customer']['CustomerID'], 'Completed', 'Rejected',))
    previousorders = cursor.fetchall()

    # In Case No Records Exist For Customer, Look For That Later!
    # if previousorders == None and currentorders == None: 
    #     flash("There are no previous orders for this account.", 'danger')
    #     return redirect(url_for('customer.customer_dashboard'))

    # Conversion of sqlite3.Row objects to Dictionaries
    currentorders = [dict(order) for order in currentorders]
    for order in currentorders:
        order['CreatedAt'] = datetime.strptime(order['CreatedAt'], '%Y-%m-%d %H:%M:%S.%f')
    previousorders = [dict(order) for order in previousorders]
    for order in previousorders:
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

    for order2 in previousorders:
        cursor.execute('''
            SELECT i.Name, oi.Quantity
            FROM OrderItems oi
            JOIN items i ON oi.ItemID = i.ItemID
            WHERE oi.OrderID = ?
        ''', (order2['OrderID'],))
        order2['Items'] = cursor.fetchall()
    
    conn.close()
    return render_template('past_orders.html', currentorders=currentorders, previousorders=previousorders)
