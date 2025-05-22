# Simple IRC Client

A lightweight command-line IRC client written in Python with basic functionality.

## Features

- Connect to IRC servers
- Join and leave channels
- Send public messages to channels
- Send private messages to users
- List available channels
- Basic proxy support (requires PySocks)
- Web GUI interface (requires Flask)

## Requirements

- Python 3.x
- Required for Web GUI: Flask, Flask-SocketIO, and Eventlet
- Optional: PySocks library (for proxy support)

## Installation

No installation required to use the basic CLI, just clone or download this repository:

```powershell
git clone https://github.com/yourusername/IRC_Client.git
cd IRC_Client
```

### Setting up a Virtual Environment (Recommended)

It's recommended to use a virtual environment to manage dependencies:

```powershell
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
.\venv\Scripts\Activate.ps1

# Install all dependencies
pip install -r requirements.txt
```

If you want to use just the CLI with proxy features:

```powershell
pip install PySocks
```

## Usage

### Basic Connection (CLI)

```powershell
python .\irc_client.py -n your_nickname
```

This connects to the default server (irc.libera.chat) on port 6667.

### Web GUI

To use the web-based GUI:

```powershell
# Make sure you've activated your virtual environment and installed dependencies
python .\irc_client_gui.py
```

Then open your web browser and navigate to http://localhost:5000. You can connect to IRC servers, join channels, and send messages through the web interface.

### Advanced Options

```powershell
python .\irc_client.py -n your_nickname -s irc.example.com -p 6697 -u username -r "Real Name"
```

### Using Proxy Support

```powershell
python .\irc_client.py -n your_nickname --proxy-type socks5 --proxy-host 127.0.0.1 --proxy-port 9050
```

For authenticated proxies:

```powershell
python .\irc_client.py -n your_nickname --proxy-type socks5 --proxy-host 127.0.0.1 --proxy-port 9050 --proxy-username user --proxy-password-prompt
```

## Available Commands

Once connected, you can use these commands:

| Command | Description |
|---------|-------------|
| `/join #channel` | Join a channel |
| `/leave [#channel]` | Leave current or specified channel |
| `/msg target message` | Send a private message |
| `/raw command` | Send a raw IRC command |
| `/list` | List available channels |
| `/help` | Show help message |
| `/quit` or `/exit` | Disconnect and exit |

Messages not starting with `/` are sent to the current channel.

## Example Session

1. Connect to the server:
   ```
   python .\irc_client.py -n test_user
   ```

2. Join a channel:
   ```
   /join #libera
   ```

3. Send a message to the channel:
   ```
   Hello, world!
   ```

4. Send a private message:
   ```
   /msg nickname Hello there!
   ```

5. Leave a channel:
   ```
   /leave
   ```

6. Disconnect:
   ```
   /quit
   ```

## Notes

- If the nickname is already registered on the server, it might be changed automatically.
- The `/list` command may return a large amount of data on busy servers.
- The proxy support requires the PySocks library; without it, the client will run in non-proxy mode.

## License

[WTFPL](LICENSE) - Do What The F*** You Want To Public License
