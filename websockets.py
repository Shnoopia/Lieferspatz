from flask_socketio import emit, join_room, leave_room
from flask import session
from db import get_db_connection

def setup_socket_events(socketio):
    @socketio.on('join_room')
    def handle_join(data):
        room = data['room']
        join_room(room)
        emit('room_joined', {'message': f'Joined room: {room}'}, room=room)

    @socketio.on('send_payment')
    def handle_payment(data):
        customer_id = session['customer']['CustomerID']
        customer_name = f"{session['customer']['FirstName']} {session['customer']['LastName']}"
        restaurant_id = session['chosenrestID']
        room = f'restaurant_{restaurant_id}'
        emit('payment_received', {
            'customer_id': customer_id,
            'customer_name': customer_name,
            'message': data['message']
        }, room=room)

    @socketio.on('restaurant_reply')
    def handle_restaurant_reply(data):
        customer_id = data['customer_id']
        room = f'customer_{customer_id}'
        emit('restaurant_ack', {
            'message': data['message']
        }, room=room)