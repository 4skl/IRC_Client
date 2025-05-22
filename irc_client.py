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
        
        elif command == '433':  # Nickname already in use
            self.nickname = self.nickname + "_"
            print(f"Nickname already in use, trying {self.nickname}")
            self.send(f"NICK {self.nickname}")

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
                        
                    elif command == "help":
                        print("Available commands:")
                        print("  /join <channel> - Join a channel")
                        print("  /leave [channel] - Leave current or specified channel")
                        print("  /msg <target> <message> - Send a private message")
                        print("  /raw <command> - Send a raw IRC command")
                        print("  /list - List available channels")
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