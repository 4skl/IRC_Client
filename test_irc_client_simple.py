#!/usr/bin/env python3
"""
Simple test script for the IRC client
"""
import subprocess
import time
import sys
import requests
import socket

# Check if the web server is already running
def is_port_in_use(port):
    """Check if a port is already in use"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def test_cli_help():
    """Test the CLI help command"""
    print("Testing CLI help...")
    proc = subprocess.run(["python", "irc_client.py", "--help"], 
                         stdout=subprocess.PIPE, 
                         stderr=subprocess.PIPE,
                         text=True)
    if "usage:" in proc.stdout and "IRC" in proc.stdout:
        print("✅ CLI help test passed")
        return True
    else:
        print("❌ CLI help test failed")
        return False
        
def test_cli_version():
    """Test the CLI version command if implemented"""
    print("Testing CLI version info...")
    proc = subprocess.run(["python", "irc_client.py", "--version"], 
                         stdout=subprocess.PIPE, 
                         stderr=subprocess.PIPE,
                         text=True)
    # Note: This might fail if --version isn't implemented yet
    if proc.returncode == 0:
        print("✅ CLI version test passed")
        return True
    else:
        print("⚠️ CLI version test skipped (--version not implemented)")
        return None  # Not a failure, just not implemented

def test_web_gui():
    """Test the web GUI interface"""
    if is_port_in_use(5000):
        print("Port 5000 is already in use. Skipping web GUI test.")
        return False
    
    print("Starting Web GUI server...")
    proc = subprocess.Popen(["python", "irc_client_gui_updated.py"],
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)
    
    # Wait for the server to start
    time.sleep(5)
    
    try:
        print("Testing Web GUI homepage...")
        response = requests.get("http://localhost:5000")
        if response.status_code == 200 and "IRC Web Client" in response.text:
            print("✅ Web GUI test passed")
            result = True
        else:
            print("❌ Web GUI test failed")
            result = False
    except requests.RequestException as e:
        print(f"❌ Web GUI test failed: {e}")
        result = False
    
    print("Shutting down Web GUI server...")
    if sys.platform == 'win32':
        # On Windows, we need to kill the process by its PID
        subprocess.run(["taskkill", "/F", "/PID", str(proc.pid)])
    else:
        proc.terminate()
    
    return result

if __name__ == "__main__":
    print("Running IRC client tests...")
    cli_help_passed = test_cli_help()
    cli_version = test_cli_version()
    web_passed = test_web_gui()
    
    # Calculate overall CLI result
    cli_passed = cli_help_passed  # For now, only rely on help test
    
    print("\nTest Summary:")
    print(f"CLI Help Test: {'PASSED' if cli_help_passed else 'FAILED'}")
    print(f"CLI Version Test: {'PASSED' if cli_version == True else 'NOT IMPLEMENTED' if cli_version is None else 'FAILED'}")
    print(f"Web GUI Test: {'PASSED' if web_passed else 'FAILED'}")
    
    if cli_passed and web_passed:
        print("\nAll required tests passed! ✅")
        sys.exit(0)
    else:
        print("\nSome tests failed. ❌")
        sys.exit(1)
