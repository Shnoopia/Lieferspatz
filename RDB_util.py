import sqlite3
from datetime import datetime
from flask import session

def connect_to_database():
    conn = sqlite3.connect('lieferspatz.db',isolation_level=None)
    return conn
    
def add_item_to_database(Name, Price, Description, ImageURL, Category):
    conn = connect_to_database()
    conn.execute('''
            INSERT INTO Items (Name,
                    RestaurantID,
                    Price,
                    Description,
                    ImageURL,
                    Category,
                    CreatedAt)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (Name, session['user_id'], Price, Description,ImageURL, Category, datetime.now()))
    conn.commit()
    conn.close()

def update_item_to_database(Name, Price, Description, ImageURL,ItemID):
    conn = connect_to_database()
    conn.execute('''
            UPDATE Items 
            Set Name = ?, Price = ?,Description = ?, ImageURL = ?
            WHERE ItemID = ?
        ''', (Name, Price, Description,ImageURL, ItemID))
    conn.commit()
    conn.close()


def get_all_items_from_database():
    conn = connect_to_database()
    cursor  = conn.cursor()

    cursor.execute("SELECT ItemID, Name, Price, Description, CreatedAt, ImageURL, Category FROM Items WHERE RestaurantID = ?", (session['user_id'],))
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_item_from_database(ItemID):
    conn = connect_to_database()
    cursor  = conn.cursor()
    cursor.execute("SELECT ItemID, Name, Price, Description, CreatedAt, ImageURL FROM Items WHERE ItemID = ?", (ItemID,))
    row = cursor.fetchall()
    conn.close()
    return row

def delete_item_from_database(ItemID):
    conn = connect_to_database()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Items WHERE ItemID = ?", ItemID)
    conn.commit()
    conn.close()

def get_all_orders_from_database():
    conn = connect_to_database()
    cursor  = conn.cursor()

    cursor.execute("SELECT * FROM Orders WHERE RestaurantID = ?", (session['user_id'],))
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_customer(CustomerID):
    conn = connect_to_database()
    cursor  = conn.cursor()
    cursor.execute("SELECT FirstName, LastName FROM Customers WHERE CustomerID = ?", (CustomerID,))
    rows = cursor.fetchall()
    conn.close()
    return rows