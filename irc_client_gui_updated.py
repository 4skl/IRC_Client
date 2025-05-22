#!/usr/bin/env python3
"""
Web GUI for the IRC Client
"""
import os
import json
import re
import shutil
from threading import Lock
from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO, emit
from irc_client import IRCClient

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24).hex()  # Generate a random secret key
socketio = SocketIO(app, cors_allowed_origins="*")

# Store client instances - key is session ID
clients = {}
clients_lock = Lock()

# Message buffer for each client (session)
message_buffers = {}

# Make sure templates directory exists
if not os.path.exists('templates'):
    os.makedirs('templates')

# Use enhanced template if it exists, otherwise copy from index_enhanced.html
if not os.path.exists('templates/index.html') and os.path.exists('templates/index_enhanced.html'):
    shutil.copyfile('templates/index_enhanced.html', 'templates/index.html')
    print("Using enhanced template for the web interface")


@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')


@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    session_id = request.sid
    with clients_lock:
        if session_id not in clients:
            message_buffers[session_id] = []
    emit('status', {'message': 'Connected to IRC Web GUI'})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    session_id = request.sid
    with clients_lock:
        if session_id in clients:
            client = clients[session_id]
            client.disconnect()
            del clients[session_id]
            if session_id in message_buffers:
                del message_buffers[session_id]


@socketio.on('connect_to_server')
def handle_connect_to_server(data):
    """Connect to IRC server"""
    server = data.get('server', 'irc.libera.chat')
    port = int(data.get('port', 6667))
    nickname = data.get('nickname')
    username = data.get('username', nickname)
    realname = data.get('realname', nickname)
    
    # Proxy settings
    proxy_type = data.get('proxy_type')
    proxy_host = data.get('proxy_host')
    proxy_port = data.get('proxy_port')
    if proxy_port and proxy_port.isdigit():
        proxy_port = int(proxy_port)
    proxy_username = data.get('proxy_username')
    proxy_password = data.get('proxy_password')
    
    if not nickname:
        emit('error', {'message': 'Nickname is required'})
        return
    
    session_id = request.sid
    
    # Create a custom message handler for this client
    def message_handler(message):
        with clients_lock:
            if session_id in message_buffers:
                message_buffers[session_id].append(message)
                socketio.emit('message', {'message': message}, room=session_id)
    
    # Create IRC client
    client = CustomIRCClient(
        server=server,
        port=port,
        nickname=nickname,
        username=username,
        realname=realname,
        proxy_type=proxy_type,
        proxy_host=proxy_host,
        proxy_port=proxy_port,
        proxy_username=proxy_username,
        proxy_password=proxy_password,
        message_callback=message_handler
    )
    
    # Set session ID and connect to server
    client.session_id = session_id
    success = client.connect()
    
    if success:
        with clients_lock:
            clients[session_id] = client
        emit('status', {'message': f'Connected to {server}:{port}'})
    else:
        emit('error', {'message': f'Failed to connect to {server}:{port}'})


@socketio.on('join_channel')
def handle_join_channel(data):
    """Join an IRC channel"""
    channel = data.get('channel', '')
    session_id = request.sid
    
    with clients_lock:
        if session_id not in clients:
            emit('error', {'message': 'Not connected to any server'})
            return
        
        client = clients[session_id]
        client.join_channel(channel)
        emit('status', {'message': f'Joined channel {channel}'})


@socketio.on('leave_channel')
def handle_leave_channel(data):
    """Leave an IRC channel"""
    channel = data.get('channel', '')
    session_id = request.sid
    
    with clients_lock:
        if session_id not in clients:
            emit('error', {'message': 'Not connected to any server'})
            return
        
        client = clients[session_id]
        if not channel and client.current_channel:
            channel = client.current_channel
        
        if channel:
            client.leave_channel(channel)
            emit('status', {'message': f'Left channel {channel}'})
        else:
            emit('error', {'message': 'No channel specified and not in any channel'})


@socketio.on('send_message')
def handle_send_message(data):
    """Send a message to a channel or user"""
    target = data.get('target', '')
    message = data.get('message', '')
    session_id = request.sid
    
    with clients_lock:
        if session_id not in clients:
            emit('error', {'message': 'Not connected to any server'})
            return
        
        client = clients[session_id]
        if not target and client.current_channel:
            target = client.current_channel
        
        if target and message:
            client.send_message(target, message)
        else:
            emit('error', {'message': 'Target and message are required'})


@socketio.on('send_command')
def handle_send_command(data):
    """Handle IRC commands"""
    command = data.get('command', '').strip()
    session_id = request.sid
    
    if not command:
        emit('error', {'message': 'No command provided'})
        return
    
    with clients_lock:
        if session_id not in clients:
            emit('error', {'message': 'Not connected to any server'})
            return
        
        client = clients[session_id]
        
        # Process command
        if command.startswith('/'):
            command = command[1:]  # Remove leading slash
            parts = command.split(' ', 1)
            cmd = parts[0].lower()
            args = parts[1] if len(parts) > 1 else ""
            
            if cmd == "join":
                if args:
                    client.join_channel(args)
                    emit('status', {'message': f'Joined channel {args}'})
                else:
                    emit('error', {'message': 'Usage: /join <channel>'})
                    
            elif cmd == "leave" or cmd == "part":
                if args:
                    client.leave_channel(args)
                    emit('status', {'message': f'Left channel {args}'})
                elif client.current_channel:
                    channel = client.current_channel
                    client.leave_channel(channel)
                    emit('status', {'message': f'Left channel {channel}'})
                else:
                    emit('error', {'message': 'Not in any channel'})
            
            elif cmd == "msg" or cmd == "query":
                msg_parts = args.split(' ', 1)
                if len(msg_parts) == 2:
                    target, msg = msg_parts
                    client.send_message(target, msg)
                else:
                    emit('error', {'message': 'Usage: /msg <target> <message>'})
            
            elif cmd == "raw":
                if args:
                    client.send(args)
                else:
                    emit('error', {'message': 'Usage: /raw <command>'})
            
            elif cmd == "list":
                emit('status', {'message': 'Requesting channel list from server...'})
                client.send("LIST")
                
            elif cmd == "topic":
                if args:
                    parts = args.split(' ', 1)
                    if len(parts) == 1:
                        # Get topic
                        channel = parts[0]
                        client.get_channel_topic(channel)
                    elif len(parts) == 2:
                        # Set topic
                        channel, topic = parts
                        client.set_channel_topic(channel, topic)
                elif client.current_channel:
                    client.get_channel_topic(client.current_channel)
                else:
                    emit('error', {'message': 'Usage: /topic <channel> [topic]'})
                    
            elif cmd == "help":
                help_text = """Available commands:
/join #channel - Join a channel
/leave [#channel] - Leave current or specified channel
/msg target message - Send a private message
/raw command - Send a raw IRC command
/list - List available channels
/topic [channel] [topic] - View or set channel topic
/quit - Disconnect from server
/help - Show this help message"""
                emit('help', {'message': help_text})
                
            elif cmd == "quit":
                client.disconnect()
                emit('status', {'message': 'Disconnected from server'})
                with clients_lock:
                    if session_id in clients:
                        del clients[session_id]
            
            else:
                # Send raw command
                client.send(command)
        else:
            # Not a command, send as message to current channel
            if client.current_channel:
                client.send_message(client.current_channel, command)
            else:
                emit('error', {'message': 'Not in any channel. Join a channel first with /join.'})


@socketio.on('disconnect_from_server')
def handle_disconnect_from_server():
    """Disconnect from IRC server"""
    session_id = request.sid
    
    with clients_lock:
        if session_id in clients:
            client = clients[session_id]
            client.disconnect()
            del clients[session_id]
            emit('status', {'message': 'Disconnected from server'})
        else:
            emit('error', {'message': 'Not connected to any server'})


class CustomIRCClient(IRCClient):
    """Extended IRC client with custom message handling"""
    
    def __init__(self, server, port, nickname, username=None, realname=None,
                 proxy_type=None, proxy_host=None, proxy_port=None,
                 proxy_username=None, proxy_password=None, message_callback=None):
        super().__init__(server, port, nickname, username, realname,
                         proxy_type, proxy_host, proxy_port,
                         proxy_username, proxy_password)
        self.message_callback = message_callback
        self.session_id = None
    
    def process_message(self, message):
        """Override process_message to call the callback and handle special messages"""
        # Call the original implementation
        super().process_message(message)
        
        # Parse IRC message
        match = re.match(r'^(?::([^ ]+) )?([^ ]+)(?: ((?:[^: ][^ ]* ?)*))?(?: :(.*))?$', message)
        if match:
            prefix, command, params_str, trailing = match.groups()
            params = (params_str or '').split() 
            if trailing:
                params.append(trailing)
            
            # Handle specific responses that we want to send to the client
            
            # Channel topic (332)
            if command == '332' and len(params) >= 3:
                channel = params[1]
                topic = params[2]
                if self.session_id:
                    socketio.emit('channel_topic', {
                        'channel': channel,
                        'topic': topic
                    }, room=self.session_id)
            
            # Names reply (list of users in channel) - 353
            elif command == '353' and len(params) >= 4:
                channel = params[2]
                users = params[3].split()
                
                if self.session_id and channel in self.channel_users:
                    socketio.emit('user_list', {
                        'channel': channel,
                        'users': list(self.channel_users[channel])
                    }, room=self.session_id)
        
        # Call the callback if it exists
        if self.message_callback:
            self.message_callback(message)


@socketio.on('get_channel_list')
def handle_get_channel_list():
    """Get the list of joined channels"""
    session_id = request.sid
    
    with clients_lock:
        if session_id not in clients:
            emit('error', {'message': 'Not connected to any server'})
            return
        
        client = clients[session_id]
        channel_list = list(client.channels)
        current_channel = client.current_channel
        
        emit('channel_list', {
            'channels': channel_list,
            'current_channel': current_channel
        })


@socketio.on('get_user_list')
def handle_get_user_list(data):
    """Get the list of users in a channel"""
    channel = data.get('channel', '')
    session_id = request.sid
    
    with clients_lock:
        if session_id not in clients:
            emit('error', {'message': 'Not connected to any server'})
            return
        
        client = clients[session_id]
        if not channel and client.current_channel:
            channel = client.current_channel
            
        if channel:
            # Get users from the client's cache
            users = list(client.get_channel_users(channel))
            emit('user_list', {'channel': channel, 'users': users})
            
            # Also request an updated list from the server
            client.send(f"NAMES {channel}")
        else:
            emit('error', {'message': 'No channel specified and not in any channel'})


@socketio.on('get_channel_topic')
def handle_get_channel_topic(data):
    """Get the topic of a channel"""
    channel = data.get('channel', '')
    session_id = request.sid
    
    with clients_lock:
        if session_id not in clients:
            emit('error', {'message': 'Not connected to any server'})
            return
        
        client = clients[session_id]
        if not channel and client.current_channel:
            channel = client.current_channel
            
        if channel:
            # Get topic from the client's cache
            topic = client.get_topic(channel)
            if topic:
                emit('channel_topic', {'channel': channel, 'topic': topic})
            
            # Also request an updated topic from the server
            client.get_channel_topic(channel)
        else:
            emit('error', {'message': 'No channel specified and not in any channel'})


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)
