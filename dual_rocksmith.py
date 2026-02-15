#!/usr/bin/env python3
# Compatible with Python 3.6+

import subprocess
import time
import threading
import sys
import psutil
import os
import signal

# Define paths and commands
ALSA_CMD = ["alsa_in", "-j", "RTC_2", "-d", "hw:Adapter_1", "-r", "48000", "-c", "1"]
LAUNCHER_PATH = "/home/chris/.local/share/Steam/steamapps/common/rocksmith-launcher.sh"

def monitor_alsa_output(proc):
    """
    Reads output from alsa_in process line by line.
    Exits the program if specific error is found.
    """
    try:
        # Read lines as they become available
        for line in iter(proc.stdout.readline, ''):
            # Print alsa output for debugging/visibility
            print(f"[ALSA_IN] {line.strip()}")
            
            if "err = -11" in line:
                print("\n[ERROR] Alsa error detected (err = -11). Please restart.")
                # Kill alsa_in process before exiting
                proc.terminate()
                os._exit(1)
    except Exception as e:
        print(f"Error reading alsa output: {e}")

def check_rocksmith_process():
    """Checks if Rocksmith2014.exe is running using psutil."""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            # Check name
            if proc.info['name'] and 'Rocksmith2014' in proc.info['name']:
                return True
            # Check command line arguments (often needed for Wine/Proton apps)
            cmdline = proc.info['cmdline']
            if cmdline:
                for arg in cmdline:
                    if 'Rocksmith2014' in arg:
                        return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return False

def check_jack_ports():
    """Checks if Rocksmith's JACK ports are available."""
    try:
        # Capture both stdout and stderr
        proc = subprocess.Popen(["jack_lsp"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        stdout, stderr = proc.communicate()
        if "Rocksmith2014:in_1" in stdout:
            print("\n--- Current JACK Ports ---")
            print(stdout)
            if stderr:
                print("--- JACK LSP Errors ---")
                print(stderr)
            return True
    except Exception as e:
        print(f"Error checking ports: {e}")
    return False

def connect_jack_ports():
    """Automatically connects physical inputs to Rocksmith inputs."""
    print("Connecting JACK ports...")
    
    connections = [
        ("RTC_2:capture_1", "Rocksmith2014:in_2")
    ]
    
    for src, dst in connections:
        print(f"Executing: jack_connect {src} {dst}")
        try:
            proc = subprocess.Popen(["jack_connect", src, dst], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            stdout, stderr = proc.communicate()
            if stdout:
                print(f"STDOUT: {stdout.strip()}")
            if stderr:
                print(f"STDERR: {stderr.strip()}")
            if proc.returncode == 0:
                print(f"Successfully connected {src} to {dst}")
            else:
                print(f"Failed to connect {src} to {dst} (Exit code: {proc.returncode})")
        except Exception as e:
            print(f"Exception during connection: {e}")


def main():
    print("Starting Dual Rocksmith Setup (Python Port)...")

    # 1. Start Rocksmith Launcher (Detached / Nohup style)
    print(f"Launching Rocksmith from: {LAUNCHER_PATH}")
    try:
        subprocess.Popen(
            [LAUNCHER_PATH],
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except FileNotFoundError:
        print(f"Error: Launcher script not found at {LAUNCHER_PATH}")
        sys.exit(1)

    # 2. Start alsa_in and monitor output
    print(f"Starting alsa_in: {' '.join(ALSA_CMD)}")
    try:
        alsa_proc = subprocess.Popen(
            ALSA_CMD,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, 
            universal_newlines=True,
            bufsize=1
        )
    except FileNotFoundError:
        print("Error: alsa_in command not found.")
        sys.exit(1)

    # Start monitoring thread for alsa_in
    monitor_thread = threading.Thread(target=monitor_alsa_output, args=(alsa_proc,), daemon=True)
    monitor_thread.start()

    print("Phase 1: Waiting for Rocksmith2014 to start...")
    while not check_rocksmith_process():
        time.sleep(1)
    
    print("Rocksmith detected! Waiting 30 seconds for total system stabilization...")
    time.sleep(30)

    print("Phase 2: Connecting and monitoring.")
    ports_connected = False
    consecutive_missing_checks = 0

    try:
        while True:
            is_running = check_rocksmith_process()
            
            if is_running:
                consecutive_missing_checks = 0
                # Try to connect ports if not already done
                if not ports_connected:
                    connect_jack_ports()
                    ports_connected = True
            else:
                consecutive_missing_checks += 1
                if consecutive_missing_checks >= 10: # Game must be gone for 10 seconds straight
                    print("Rocksmith process disappeared for 10s. Cleaning up...")
                    break
                else:
                    # Optional: print(f"Warning: Game not seen (Attempt {consecutive_missing_checks}/10)")
                    pass

            time.sleep(1)

    except KeyboardInterrupt:
        print("\nStopping script...")
    finally:
        # Cleanup
        if alsa_proc.poll() is None:
            print("Terminating alsa_in...")
            alsa_proc.terminate()
            try:
                alsa_proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                alsa_proc.kill()

if __name__ == "__main__":
    main()
