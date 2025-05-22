# Simple IRC Client

A lightweight command-line and web-based IRC client written in Python with both basic and advanced functionality.

## Features

- Connect to IRC servers
- Join and leave channels
- Send public messages to channels
- Send private messages to users
- List available channels
- Display and set channel topics
- Track users in channels with proper mode display (operators, voiced users)
- Basic proxy support (requires PySocks)
- Web GUI interface with real-time updates

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
python .\irc_client_gui_updated.py  # Use the updated version with all features
```

Then open your web browser and navigate to http://localhost:5000. The web interface provides:

- Server connection with optional proxy support
- Channel joining/leaving
- Real-time message display with proper formatting
- User list with role indicators (operators, voiced users)
- Channel topic display and management
- Support for standard IRC commands

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
| `/topic [#channel] [new topic]` | View or set channel topic |
| `/help` | Show help message |
| `/quit` or `/exit` | Disconnect and exit |

Messages not starting with `/` are sent to the current channel.

### Web Interface Features

The web interface provides additional functionality:

- **Channel List**: Click on any channel in the sidebar to switch between joined channels
- **User List**: 
  - View all users in the current channel with their mode indicators
  - @ for channel operators (shown in red)
  - + for voiced users (shown in green)
  - Click on a username to start a private message
- **Topic Display**: View the current channel's topic at the top of the message area
- **Message Formatting**: Different message types (errors, system messages, private messages) use different colors for easy reading

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

## Testing

To test the IRC client functionality, run the test scripts:

```powershell
# Simple test for both CLI and GUI interfaces
python .\test_irc_client_simple.py

# More comprehensive tests
python .\test_irc_client_all.py
```

## File Structure

- `irc_client.py` - Core IRC client implementation
- `irc_client_gui_updated.py` - Latest version of the web GUI (recommended)
- `irc_client_gui.py` - Original web GUI implementation
- `templates/index.html` - HTML template for the web interface
- `templates/index_enhanced.html` - Enhanced template with user list and topic display
- `test_irc_client_simple.py` - Simple test script for both interfaces

## License

[WTFPL](LICENSE) - Do What The F*** You Want To Public License

## Donations (optional)

If you find this project useful, please consider making a donation to support its development.

XMR (Monero): 83fxvbkP8M1DzRSEtoEqNN9qmMD7c1HN1G535GLx424dQGZj3dagHqbP9T2yRF3c9BMV3LZ2s7zHYF9cWBRfCraLBt9EdRq
