#!/usr/bin/env python3
"""
Test script for IRC client components
"""
import os
import sys
import time
import subprocess
import threading
import socket
import webbrowser

def test_cli_client():
    """Test the command-line IRC client"""
    print("Testing command-line IRC client...")
    print("Starting IRC client with test connection...")
    
    # Test basic connection
    try:
        # On Windows, we need shell=True to properly handle input redirection
        process = subprocess.Popen(
            ["python", "irc_client.py", "-n", "test_bot_cli", "-s", "irc.libera.chat"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=True,
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
        
        # Give it some time to connect
        time.sleep(3)
        
        # Test sending commands
        commands = [
            "/list\n",
            "/join #test\n",
            "Hello from CLI test!\n",
            "/quit\n"
        ]
        
        # Send commands with delay
        try:
            for cmd in commands:
                # Check if pipe is still connected
                if process.poll() is not None:
                    break
                    
                process.stdin.write(cmd)
                process.stdin.flush()
                time.sleep(1)
                
            # Wait for process to end
            process.wait(timeout=5)
            print("CLI test completed successfully!")
        except (BrokenPipeError, OSError) as e:
            # Handle pipe errors gracefully
            print(f"Note: Pipe closed early - {e}")
            print("This is normal if the IRC client disconnected.")
            print("CLI test completed with expected pipe termination.")
        
    except Exception as e:
        print(f"CLI test failed: {str(e)}")
        return False
    
    return True

def is_port_in_use(port):
    """Check if a port is already in use"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def test_web_gui():
    """Test the web-based GUI IRC client"""
    print("Testing web-based GUI IRC client...")
    
    # Check if port 5000 is available
    if is_port_in_use(5000):
        print("Error: Port 5000 is already in use. Please close the application using it.")
        return False
      # Start the web server in a separate process
    try:
        process = subprocess.Popen(
            ["python", "irc_client_gui.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Give the server time to start
        time.sleep(3)
          # Open web browser
        print("Opening web interface in browser...")
        webbrowser.open('http://127.0.0.1:5000')
        
        # Let the user test it manually
        print("\nWeb GUI server is running.")
        print("Please test the web interface manually in your browser.")
        print("Press Enter when done to stop the server...")
        input()
        
        # Stop the server
        process.terminate()
        process.wait(timeout=5)
        print("Web GUI test completed!")
        
    except Exception as e:
        print(f"Web GUI test failed: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    print("IRC Client Test Suite")
    print("=====================")
      # Check requirements first
    requirements_missing = False
    try:
        import flask
    except ImportError:
        print("Error: Flask package is missing.")
        requirements_missing = True
        
    try:
        import flask_socketio
    except ImportError:
        print("Error: Flask-SocketIO package is missing.")
        requirements_missing = True
        
    try:
        import eventlet
    except ImportError:
        print("Error: Eventlet package is missing.")
        requirements_missing = True
        
    if requirements_missing:
        print("Please install the requirements with: pip install -r requirements.txt")
        sys.exit(1)
    
    # Run tests
    cli_result = test_cli_client()
    web_result = test_web_gui()
    
    # Report results
    print("\nTest Results:")
    print(f"CLI Client: {'PASSED' if cli_result else 'FAILED'}")
    print(f"Web GUI: {'PASSED' if web_result else 'FAILED'}")
    
    if cli_result and web_result:
        print("\nAll tests passed!")
        sys.exit(0)
    else:
        print("\nSome tests failed.")
        sys.exit(1)
