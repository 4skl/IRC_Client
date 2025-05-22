#!/usr/bin/env python3
"""
Web GUI for the IRC Client
"""
import os
import json
import re
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
    
    # Connect to server
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
                
            elif cmd == "help":
                help_text = """Available commands:
/join #channel - Join a channel
/leave [#channel] - Leave current or specified channel
/msg target message - Send a private message
/raw command - Send a raw IRC command
/list - List available channels
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


# Create templates directory if it doesn't exist
if not os.path.exists('templates'):
    os.makedirs('templates')

# Create the index.html template
with open('templates/index.html', 'w') as f:
    f.write('''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IRC Web Client</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            display: flex;
            flex-direction: column;
            height: 100vh;
            background-color: #f5f5f5;
        }
        .container {
            display: flex;
            flex: 1;
            overflow: hidden;
        }
        .sidebar {
            width: 200px;
            background-color: #2c3e50;
            color: white;
            padding: 10px;
            overflow-y: auto;
        }
        .main-content {
            flex: 1;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        .message-area {
            flex: 1;
            padding: 10px;
            overflow-y: auto;
            background-color: white;
            border-bottom: 1px solid #ddd;
        }
        .input-area {
            padding: 10px;
            background-color: #f9f9f9;
            border-top: 1px solid #ddd;
        }
        .connection-form {
            padding: 10px;
            background-color: #f0f0f0;
            border-bottom: 1px solid #ddd;
        }
        input[type="text"], input[type="number"], input[type="password"] {
            padding: 8px;
            margin: 5px 0;
            border: 1px solid #ddd;
            border-radius: 3px;
        }
        button {
            padding: 8px 15px;
            background-color: #3498db;
            color: white;
            border: none;
            border-radius: 3px;
            cursor: pointer;
        }
        button:hover {
            background-color: #2980b9;
        }
        .message {
            margin: 5px 0;
            padding: 5px;
            border-radius: 3px;
        }
        .system-message {
            color: #7f8c8d;
            font-style: italic;
        }
        .error-message {
            color: #e74c3c;
        }
        .help-header, .help-footer {
            color: #3498db;
            font-weight: bold;
        }
        .help-message {
            color: #2c3e50;
            font-family: monospace;
            margin-left: 10px;
        }
        .list-message {
            color: #16a085;
        }
        .chat-message {
            color: #34495e;
        }
        .private-message {
            color: #8e44ad;
            font-style: italic;
        }
        .channel-list {
            list-style-type: none;
            padding: 0;
            margin: 10px 0;
        }
        .channel-list li {
            padding: 5px;
            cursor: pointer;
        }
        .channel-list li:hover {
            background-color: #34495e;
        }
        .channel-list li.active {
            background-color: #3498db;
        }
        #message-input {
            width: calc(100% - 100px);
        }
        .toggle-button {
            margin-top: 10px;
            background-color: #7f8c8d;
        }
        .advanced-options {
            display: none;
            margin-top: 10px;
            padding: 10px;
            background-color: #e8e8e8;
            border-radius: 3px;
        }
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.5);
        }
        .modal-content {
            background-color: white;
            margin: 15% auto;
            padding: 20px;
            width: 80%;
            max-width: 500px;
            border-radius: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="sidebar">
            <h3>Channels</h3>
            <ul id="channel-list" class="channel-list">
                <!-- Channels will be added here -->
            </ul>
            <h3>Users</h3>
            <ul id="user-list" class="channel-list">
                <!-- Users will be added here -->
            </ul>
        </div>
        <div class="main-content">
            <div class="connection-form">
                <h3>Connect to IRC Server</h3>
                <div>
                    <input type="text" id="server" placeholder="Server (default: irc.libera.chat)" value="irc.libera.chat">
                    <input type="number" id="port" placeholder="Port (default: 6667)" value="6667">
                    <input type="text" id="nickname" placeholder="Nickname (required)" required>
                    <button id="connect-btn">Connect</button>
                    <button id="disconnect-btn" disabled>Disconnect</button>
                </div>
                <button id="toggle-advanced" class="toggle-button">Advanced Options</button>
                <div id="advanced-options" class="advanced-options">
                    <h4>User Information</h4>
                    <input type="text" id="username" placeholder="Username (optional)">
                    <input type="text" id="realname" placeholder="Real Name (optional)">
                    
                    <h4>Proxy Settings</h4>
                    <select id="proxy-type">
                        <option value="">No Proxy</option>
                        <option value="socks4">SOCKS4</option>
                        <option value="socks5">SOCKS5</option>
                        <option value="http">HTTP</option>
                    </select>
                    <input type="text" id="proxy-host" placeholder="Proxy Host">
                    <input type="number" id="proxy-port" placeholder="Proxy Port">
                    <input type="text" id="proxy-username" placeholder="Proxy Username (optional)">
                    <input type="password" id="proxy-password" placeholder="Proxy Password (optional)">
                </div>
            </div>
            <div class="message-area" id="message-area">
                <!-- Messages will appear here -->
                <div class="message system-message">Welcome to the IRC Web Client</div>
            </div>
            <div class="input-area">
                <input type="text" id="message-input" placeholder="Type a message or command (/join, /msg, etc.)" disabled>
                <button id="send-btn" disabled>Send</button>
            </div>
        </div>
    </div>

    <!-- Join Channel Modal -->
    <div id="join-modal" class="modal">
        <div class="modal-content">
            <h3>Join Channel</h3>
            <input type="text" id="channel-name" placeholder="Channel name (e.g., #channel)">
            <button id="join-channel-btn">Join</button>
            <button id="close-modal-btn">Cancel</button>
        </div>
    </div>

    <script src="https://cdn.socket.io/4.4.1/socket.io.min.js"></script>
    <script>
        document.addEventListener('DOMContentLoaded', () => {
            const socket = io();
            const channels = new Set();
            let currentChannel = null;
            
            // DOM elements
            const messageArea = document.getElementById('message-area');
            const messageInput = document.getElementById('message-input');
            const sendBtn = document.getElementById('send-btn');
            const connectBtn = document.getElementById('connect-btn');
            const disconnectBtn = document.getElementById('disconnect-btn');
            const toggleAdvancedBtn = document.getElementById('toggle-advanced');
            const advancedOptions = document.getElementById('advanced-options');
            const channelList = document.getElementById('channel-list');
            
            // Toggle advanced options
            toggleAdvancedBtn.addEventListener('click', () => {
                advancedOptions.style.display = advancedOptions.style.display === 'none' ? 'block' : 'none';
            });
            
            // Connect to IRC server
            connectBtn.addEventListener('click', () => {
                const server = document.getElementById('server').value || 'irc.libera.chat';
                const port = parseInt(document.getElementById('port').value || '6667');
                const nickname = document.getElementById('nickname').value;
                const username = document.getElementById('username').value;
                const realname = document.getElementById('realname').value;
                
                const proxyType = document.getElementById('proxy-type').value;
                const proxyHost = document.getElementById('proxy-host').value;
                const proxyPort = document.getElementById('proxy-port').value;
                const proxyUsername = document.getElementById('proxy-username').value;
                const proxyPassword = document.getElementById('proxy-password').value;
                
                if (!nickname) {
                    addMessage('Nickname is required', 'error-message');
                    return;
                }
                
                socket.emit('connect_to_server', {
                    server,
                    port,
                    nickname,
                    username,
                    realname,
                    proxy_type: proxyType,
                    proxy_host: proxyHost,
                    proxy_port: proxyPort,
                    proxy_username: proxyUsername,
                    proxy_password: proxyPassword
                });
                
                messageInput.disabled = false;
                sendBtn.disabled = false;
                connectBtn.disabled = true;
                disconnectBtn.disabled = false;
            });
            
            // Disconnect from IRC server
            disconnectBtn.addEventListener('click', () => {
                socket.emit('disconnect_from_server');
                messageInput.disabled = true;
                sendBtn.disabled = true;
                connectBtn.disabled = false;
                disconnectBtn.disabled = true;
                channels.clear();
                updateChannelList();
                currentChannel = null;
            });
            
            // Send message or command
            sendBtn.addEventListener('click', sendMessage);
            messageInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    sendMessage();
                }
            });
            
            function sendMessage() {
                const message = messageInput.value.trim();
                if (!message) return;
                
                if (message.startsWith('/')) {
                    socket.emit('send_command', { command: message });
                } else if (currentChannel) {
                    socket.emit('send_message', {
                        target: currentChannel,
                        message: message
                    });
                } else {
                    addMessage('You are not in any channel. Join a channel first with /join.', 'error-message');
                }
                
                messageInput.value = '';
            }
            
            // Socket events
            socket.on('connect', () => {
                addMessage('Connected to IRC Web GUI', 'system-message');
            });
            
            socket.on('disconnect', () => {
                addMessage('Disconnected from IRC Web GUI', 'system-message');
                messageInput.disabled = true;
                sendBtn.disabled = true;
                connectBtn.disabled = false;
                disconnectBtn.disabled = true;
                channels.clear();
                updateChannelList();
                currentChannel = null;
            });
            
            socket.on('status', (data) => {
                addMessage(data.message, 'system-message');
                
                // Check for channel join/leave messages
                const joinMatch = data.message.match(/Joined channel (#\S+)/);
                const leaveMatch = data.message.match(/Left channel (#\S+)/);
                const disconnectMatch = data.message.match(/Disconnected from server/);
                
                if (joinMatch) {
                    const channel = joinMatch[1];
                    channels.add(channel);
                    currentChannel = channel;
                    updateChannelList();
                } else if (leaveMatch) {
                    const channel = leaveMatch[1];
                    channels.delete(channel);
                    if (currentChannel === channel) {
                        currentChannel = null;
                    }
                    updateChannelList();
                } else if (disconnectMatch) {
                    // Handle disconnect
                    messageInput.disabled = true;
                    sendBtn.disabled = true;
                    connectBtn.disabled = false;
                    disconnectBtn.disabled = true;
                    channels.clear();
                    updateChannelList();
                    currentChannel = null;
                }
            });
            
            socket.on('error', (data) => {
                addMessage(data.message, 'error-message');
            });
            
            socket.on('message', (data) => {
                // Parse IRC message
                const message = data.message;
                parseAndDisplayIRCMessage(message);
            });
            
            socket.on('help', (data) => {
                // Display help message with better formatting
                const helpLines = data.message.split('\n');
                addMessage('--- HELP ---', 'help-header');
                helpLines.forEach(line => {
                    addMessage(line, 'help-message');
                });
                addMessage('------------', 'help-footer');
            });
            
            socket.on('channel_list', (data) => {
                // Update channel list
                channels.clear();
                data.channels.forEach(channel => channels.add(channel));
                updateChannelList();
            });
            
            socket.on('user_list', (data) => {
                // Update user list in the sidebar
                const userList = document.getElementById('user-list');
                userList.innerHTML = '';
                data.users.forEach(user => {
                    const li = document.createElement('li');
                    li.textContent = user;
                    userList.appendChild(li);
                });
            });
            
            socket.on('channel_topic', (data) => {
                // Display channel topic
                const { channel, topic } = data;
                addMessage(`Topic for ${channel}: ${topic}`, 'system-message');
            });
            
            function addMessage(text, className = '') {
                const div = document.createElement('div');
                div.textContent = text;
                div.className = `message ${className}`;
                messageArea.appendChild(div);
                messageArea.scrollTop = messageArea.scrollHeight;
            }
            
            function updateChannelList() {
                channelList.innerHTML = '';
                channels.forEach(channel => {
                    const li = document.createElement('li');
                    li.textContent = channel;
                    if
