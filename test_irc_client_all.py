#!/usr/bin/env python3
"""
Test script for the IRC client (both CLI and GUI interfaces)
"""
import subprocess
import time
import sys
import os
import requests
import signal
import socket

# Configuration
CLI_COMMAND = ["python", "irc_client.py", "-n", "TestUser123", "-s", "irc.libera.chat", "-p", "6667"]
GUI_COMMAND = ["python", "irc_client_gui_updated.py"]
GUI_URL = "http://localhost:5000"
TEST_CHANNEL = "#test-channel-12345"  # Use a unique channel name to avoid conflicts

def is_port_in_use(port):
    """Check if a port is already in use"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

@contextmanager
def run_gui_server():
    """Start the GUI server and shut it down after tests"""
    if is_port_in_use(5000):
        print("Port 5000 is already in use. Please stop any running server.")
        sys.exit(1)
    
    print("Starting Web GUI server...")
    proc = subprocess.Popen(GUI_COMMAND, 
                           stdout=subprocess.PIPE, 
                           stderr=subprocess.PIPE)
    
    # Wait for the server to start
    time.sleep(5)
    
    try:
        yield proc
    finally:
        print("Shutting down Web GUI server...")
        # On Windows, you need to use CTRL_BREAK_EVENT to terminate child processes
        if sys.platform == 'win32':
            proc.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            proc.terminate()
        proc.wait(timeout=5)

class TestCLIClient(unittest.TestCase):
    """Test the command-line IRC client"""
    
    def test_cli_help(self):
        """Test that the CLI client shows help"""
        proc = subprocess.run(CLI_COMMAND + ["--help"], 
                              stdout=subprocess.PIPE, 
                              stderr=subprocess.PIPE,
                              text=True)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("usage:", proc.stdout)
        self.assertIn("IRC", proc.stdout)
    
    def test_cli_with_invalid_args(self):
        """Test CLI client with invalid arguments"""
        proc = subprocess.run(CLI_COMMAND + ["--invalid-arg"], 
                              stdout=subprocess.PIPE, 
                              stderr=subprocess.PIPE,
                              text=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("error:", proc.stderr)

class TestWebGUI(unittest.TestCase):
    """Test the web GUI interface"""
    
    def test_web_gui_home(self):
        """Test that the web GUI homepage loads"""
        with run_gui_server():
            # Wait for server to fully start
            time.sleep(2)
            
            try:
                response = requests.get(GUI_URL)
                self.assertEqual(response.status_code, 200)
                self.assertIn("IRC Web Client", response.text)
                self.assertIn("socket.io", response.text)
            except requests.RequestException as e:
                self.fail(f"Failed to connect to web GUI: {e}")

if __name__ == "__main__":
    print("Running IRC client tests...")
    unittest.main()
