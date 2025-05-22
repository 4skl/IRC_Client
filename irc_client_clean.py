import socket
import threading
import sys
import re
import argparse
import time
from getpass import getpass

"""
A simple IRC client
"""
class IRCClient:
    def __init__(self, server, port, nickname, username=None, realname=None,
                 proxy_type=None, proxy_host=None, proxy_port=None,
                 proxy_username=None, proxy_password=None):
        """Initialize IRC Client with server and proxy settings"""
        self.server = server
        self.port = port
        self.nickname = nickname
        self.username = username or nickname
        self.realname = realname or nickname
        self.channels = set()
        self.running = False
        self.socket = None
        self.current_channel = None
        # Dictionary to store users in each channel
        self.channel_users = {}
        # Dictionary to store topics for each channel
        self.channel_topics = {}
        
        # Set up proxy if specified
        if proxy_type and proxy_host and proxy_port:
            self.setup_proxy(proxy_type, proxy_host, proxy_port,
                           proxy_username, proxy_password)
    
    def setup_proxy(self, proxy_type, proxy_host, proxy_port, username=None, password=None):
        """Configure the socket to use a proxy"""
        print("Warning: Proxy support requires PySocks module. Running without proxy support.")
        # The standard socket library doesn't support proxies natively
        # Consider installing PySocks if you need proxy support
    
    def connect(self):
        """Connect to the IRC server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.server, self.port))
            
            # Register with the server
            self.send(f"NICK {self.nickname}")
            self.send(f"USER {self.username} 0 * :{self.realname}")
            
            self.running = True
            
            # Start receiving messages
            self.receive_thread = threading.Thread(target=self.receive_messages)
            self.receive_thread.daemon = True
            self.receive_thread.start()
            
            return True
        except socket.error as e:
            print(f"Connection error: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from the IRC server"""
        if self.running:
            self.send("QUIT :Leaving")
            self.running = False
            if self.socket:
                self.socket.close()
    
    def join_channel(self, channel):
        """Join an IRC channel"""
        if not channel.startswith('#'):
            channel = '#' + channel
        
        self.send(f"JOIN {channel}")
        self.channels.add(channel)
        self.current_channel = channel
    
    def leave_channel(self, channel):
        """Leave an IRC channel"""
        if not channel.startswith('#'):
            channel = '#' + channel
            
        self.send(f"PART {channel} :Leaving")
        if channel in self.channels:
            self.channels.remove(channel)
            if self.current_channel == channel:
                self.current_channel = next(iter(self.channels)) if self.channels else None
    
    def send_message(self, target, message):
        """Send a message to a channel or user"""
        self.send(f"PRIVMSG {target} :{message}")
    
    def send(self, message):
        """Send raw command to the IRC server"""
        if self.socket:
            self.socket.send((message + "\r\n").encode('utf-8'))
    
    def receive_messages(self):
        """Receive and process messages from the server"""
        buffer = ""
        
        while self.running:
            try:
                data = self.socket.recv(4096).decode('utf-8', errors='ignore')
                if not data:
                    print("Disconnected from server.")
                    self.running = False
                    break
                
                buffer += data
                lines = buffer.split("\r\n")
                buffer = lines.pop()
                
                for line in lines:
                    self.process_message(line)
                    
            except socket.error as e:
                if self.running:
                    print(f"Error receiving data: {e}")
                    self.running = False
                break
    
    def process_message(self, message):
        """Process a message from the server"""
        print(f">> {message}")
        
        # Respond to PING with PONG
        if message.startswith("PING"):
            pong = message.replace("PING", "PONG", 1)
            self.send(pong)
            return
        
        # Parse IRC message
        match = re.match(r'^(?::([^ ]+) )?([^ ]+)(?: ((?:[^: ][^ ]* ?)*))?(?: :(.*))?$', message)
        if not match:
            return
        
        prefix, command, params_str, trailing = match.groups()
        params = (params_str or '').split() 
        if trailing:
            params.append(trailing)
        
        # Handle specific responses
        if command == '001':  # Welcome message
            print(f"Successfully connected to {self.server}")
            
        elif command == '332':  # Channel topic
            if len(params) >= 3:
                channel = params[1]
                topic = params[2]
                self.channel_topics[channel] = topic
                print(f"Topic for {channel}: {topic}")
                
        elif command == '353':  # Names reply (list of users in channel)
            if len(params) >= 4:
                channel = params[2]
                users = params[3].split()
                
                if channel not in self.channel_users:
                    self.channel_users[channel] = set()
                    
                for user in users:
                    # Remove prefixes like @ (op), + (voice)
                    if user and len(user) > 0 and user[0] in '@+%&~':
                        user = user[1:]
                    self.channel_users[channel].add(user)
                    
        elif command == '366':  # End of names list
            if len(params) >= 2:
                channel = params[1]
                if channel in self.channel_users:
                    users = self.channel_users[channel]
                    print(f"Users in {channel}: {', '.join(users)}")
                    
        elif command == 'JOIN':  # User joined a channel
            if prefix:
                nick = prefix.split('!')[0]
                channel = params[0] if params else None
                if channel and channel in self.channel_users:
                    self.channel_users[channel].add(nick)
                    print(f"{nick} joined {channel}")
                    
        elif command == 'PART' or command == 'QUIT':  # User left a channel or quit
            if prefix:
                nick = prefix.split('!')[0]
                channel = params[0] if params else None
                
                if command == 'PART' and channel and channel in self.channel_users and nick in self.channel_users[channel]:
                    self.channel_users[channel].remove(nick)
                    print(f"{nick} left {channel}")
                elif command == 'QUIT':  # User quit, remove from all channels
                    for ch, users in self.channel_users.items():
                        if nick in users:
                            users.remove(nick)
                    print(f"{nick} quit")
                    
        elif command == 'NICK':  # User changed nickname
            if prefix and len(params) >= 1:
                old_nick = prefix.split('!')[0]
                new_nick = params[0]
                
                # Update the user in all channels
                for ch, users in self.channel_users.items():
                    if old_nick in users:
                        users.remove(old_nick)
                        users.add(new_nick)
                print(f"{old_nick} is now known as {new_nick}")
        
        elif command == '433':  # Nickname already in use
            self.nickname = self.nickname + "_"
            print(f"Nickname already in use, trying {self.nickname}")
            self.send(f"NICK {self.nickname}")

    def get_channel_topic(self, channel):
        """Fetch the topic for a channel"""
        if not channel.startswith('#'):
            channel = '#' + channel
            
        self.send(f"TOPIC {channel}")
    
    def set_channel_topic(self, channel, topic):
        """Set the topic for a channel if you have permission"""
        if not channel.startswith('#'):
            channel = '#' + channel
            
        self.send(f"TOPIC {channel} :{topic}")
    
    def get_channel_users(self, channel=None):
        """Get the list of users in a channel
        
        Args:
            channel: The channel to get users from. If None, uses current channel.
            
        Returns:
            A set of users or None if the channel is not joined
        """
        if not channel:
            channel = self.current_channel
            
        if not channel:
            return None
            
        if not channel.startswith('#'):
            channel = '#' + channel
            
        # Request NAMES for the channel if not already in our cache
        if channel not in self.channel_users:
            self.send(f"NAMES {channel}")
            return set()  # Return empty set for now
            
        return self.channel_users.get(channel, set())
    
    def get_topic(self, channel=None):
        """Get the topic of a channel
        
        Args:
            channel: The channel to get the topic from. If None, uses current channel.
            
        Returns:
            The topic string or None if not available
        """
        if not channel:
            channel = self.current_channel
            
        if not channel:
            return None
            
        if not channel.startswith('#'):
            channel = '#' + channel
            
        # Request topic if not in cache
        if channel not in self.channel_topics:
            self.get_channel_topic(channel)
            return None  # Return None for now
            
        return self.channel_topics.get(channel)


def main():
    """Main function to parse arguments and run the IRC client"""
    parser = argparse.ArgumentParser(description="Simple IRC Client with Proxy Support")
    
    # IRC Connection settings
    parser.add_argument("-s", "--server", default="irc.libera.chat", help="IRC server address (default: irc.libera.chat)")
    parser.add_argument("-p", "--port", type=int, default=6667, help="IRC server port (default: 6667)")
    parser.add_argument("-n", "--nickname", required=True, help="IRC nickname")
    parser.add_argument("-u", "--username", help="IRC username (default: same as nickname)")
    parser.add_argument("-r", "--realname", help="IRC real name (default: same as nickname)")
    
    # Proxy settings
    parser.add_argument("--proxy-type", choices=["socks4", "socks5", "http"], help="Proxy type")
    parser.add_argument("--proxy-host", help="Proxy server address")
    parser.add_argument("--proxy-port", type=int, help="Proxy server port")
    parser.add_argument("--proxy-username", help="Proxy authentication username")
    parser.add_argument("--proxy-password-prompt", action="store_true", help="Prompt for proxy password")
    
    args = parser.parse_args()
    
    # Get proxy password if needed
    proxy_password = None
    if args.proxy_password_prompt and args.proxy_username:
        proxy_password = getpass("Enter proxy password: ")
    
    # Create and connect the IRC client
    client = IRCClient(
        server=args.server,
        port=args.port,
        nickname=args.nickname,
        username=args.username,
        realname=args.realname,
        proxy_type=args.proxy_type,
        proxy_host=args.proxy_host,
        proxy_port=args.proxy_port,
        proxy_username=args.proxy_username,
        proxy_password=proxy_password
    )
    
    if not client.connect():
        print("Failed to connect to IRC server.")
        sys.exit(1)
    
    print(f"Connected to {args.server}:{args.port}")
    print("Type /help for available commands")
    
    try:
        # Main command loop
        while client.running:
            try:
                prefix = f"[{client.current_channel}] " if client.current_channel else ""
                user_input = input(f"{prefix}> ")
                
                if not user_input:
                    continue
                
                if user_input.startswith("/"):
                    parts = user_input[1:].split(' ', 1)
                    command = parts[0].lower()
                    args_str = parts[1] if len(parts) > 1 else ""
                    
                    if command == "quit" or command == "exit":
                        client.disconnect()
                        break
                    
                    elif command == "join":
                        if args_str:
                            client.join_channel(args_str)
                        else:
                            print("Usage: /join <channel>")
                    
                    elif command == "leave" or command == "part":
                        if args_str:
                            client.leave_channel(args_str)
                        else:
                            if client.current_channel:
                                client.leave_channel(client.current_channel)
                            else:
                                print("You are not in any channel")
                    
                    elif command == "msg" or command == "query":
                        msg_parts = args_str.split(' ', 1)
                        if len(msg_parts) == 2:
                            target, msg = msg_parts
                            client.send_message(target, msg)
                        else:
                            print("Usage: /msg <target> <message>")
                    
                    elif command == "raw":
                        if args_str:
                            client.send(args_str)
                        else:
                            print("Usage: /raw <command>")
                    
                    elif command == "list":
                        print("Requesting channel list from server...")
                        client.send("LIST")
                    
                    elif command == "topic":
                        if args_str:
                            parts = args_str.split(' ', 1)
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
                            print("Usage: /topic <channel> [topic]")
                        
                    elif command == "help":
                        print("Available commands:")
                        print("  /join <channel> - Join a channel")
                        print("  /leave [channel] - Leave current or specified channel")
                        print("  /msg <target> <message> - Send a private message")
                        print("  /raw <command> - Send a raw IRC command")
                        print("  /list - List available channels")
                        print("  /topic [channel] [topic] - View or set channel topic")
                        print("  /quit or /exit - Disconnect and exit")
                        print("  /help - Show this help message")
                    
                    else:
                        print(f"Unknown command: {command}")
                        
                else:
                    # Send message to the current channel
                    if client.current_channel:
                        client.send_message(client.current_channel, user_input)
                    else:
                        print("You are not in any channel. Join a channel first with /join.")
                        
            except EOFError:
                break
            except KeyboardInterrupt:
                break
                
    finally:
        client.disconnect()
        print("Disconnected from IRC server.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting...")
