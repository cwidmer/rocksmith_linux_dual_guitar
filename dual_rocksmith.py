#!/usr/bin/env python3
# Compatible with Python 3.6+

import subprocess
import time
import threading
import sys
import psutil
import os
import signal
import re

# Define paths and commands
ALSA_CMD = ["alsa_in", "-j", "RTC_2", "-d", "hw:Adapter_1", "-r", "48000", "-c", "1", "-q", "1"]
LAUNCHER_PATH = "/home/chris/.local/share/Steam/steamapps/common/rocksmith-launcher.sh"

# --- D-Bus Integration Logic ---

def parse_dbus_line(lines):
    """Parses a block of lines from dbus-monitor output."""
    if not lines: return None
    header = lines[0]
    if "interface=org.jackaudio.JackPatchbay" in header and "member=ClientAppeared" in header:
        for line in lines[1:]:
            match = re.search(r'string\s+"([^"]+)"', line)
            if match:
                return {'type': 'ClientAppeared', 'client_name': match.group(1)}
    return None

class DbusJackListener:
    """Non-intrusive D-Bus listener for JACK events."""
    def __init__(self, target_pattern="Rocksmith2014"):
        self.target_pattern = target_pattern
        self.process = None
        self.detected_event = threading.Event()
        self.detected_client = None
        
    def start(self):
        """Starts the dbus-monitor process."""
        # Note: Scanned elsewhere in main loop for this script version
        match_rule = "type='signal',interface='org.jackaudio.JackPatchbay',member='ClientAppeared'"
        cmd = ["dbus-monitor", "--session", match_rule]
        try:
            self.process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                universal_newlines=True, bufsize=1
            )
            threading.Thread(target=self._monitor_loop, daemon=True).start()
        except FileNotFoundError:
            print("Warning: dbus-monitor not found.")

    def _monitor_loop(self):
        if not self.process: return
        current_block = []
        for line in iter(self.process.stdout.readline, ''):
            if line.startswith("signal ") and current_block:
                event = parse_dbus_line(current_block)
                if event and self.target_pattern in event.get('client_name', ''):
                    self.detected_client = event['client_name']
                    self.detected_event.set()
                current_block = []
            current_block.append(line.strip())

    def wait_for_detection(self, timeout=None):
        return self.detected_event.wait(timeout)

    def stop(self):
        if self.process:
            self.process.terminate()

# --- Main Automation Logic ---

def monitor_alsa_output(proc):
    """Monitors alsa_in for errors."""
    try:
        for line in iter(proc.stdout.readline, ''):
            if line.strip():
                print(f"[ALSA_IN] {line.strip()}")
            if "err = -11" in line:
                print("\n[ERROR] Alsa error detected (err = -11). Please restart.")
                proc.terminate()
                os._exit(1)
    except: pass

def check_rocksmith_process():
    """Checks if Rocksmith2014.exe is running."""
    for proc in psutil.process_iter(['name', 'cmdline']):
        try:
            if proc.info['name'] and 'Rocksmith2014' in proc.info['name']: return True
            cmdline = proc.info['cmdline']
            if cmdline and any('Rocksmith2014' in arg for arg in cmdline): return True
        except: continue
    return False

def connect_jack_ports(terminal_win_id=None, rocksmith_win_id=None):
    """Automatically connects physical inputs to Rocksmith inputs."""
    if terminal_win_id:
        print(f"Switching focus to terminal ({terminal_win_id}) for connection stability...")
        try:
            subprocess.run(["wmctrl", "-i", "-a", terminal_win_id], stderr=subprocess.DEVNULL)
            time.sleep(1)
        except: pass

    print("Connecting JACK ports...")
    try:
        proc = subprocess.Popen(["jack_connect", "RTC_2:capture_1", "Rocksmith2014:in_2"], 
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        stdout, stderr = proc.communicate(timeout=5)
        if proc.returncode == 0:
            print("Successfully connected RTC_2 to Rocksmith2014:in_2")
        else:
            print(f"Failed to connect: {stderr.strip()}")
    except Exception as e:
        print(f"Error during connection: {e}")

    print("Returning focus to Rocksmith...")
    try:
        time.sleep(1)
        if rocksmith_win_id:
            subprocess.run(["wmctrl", "-i", "-a", rocksmith_win_id], stderr=subprocess.DEVNULL)
        else:
            subprocess.run(["wmctrl", "-a", "Rocksmith 2014"], stderr=subprocess.DEVNULL)
        subprocess.run(["wmctrl", "-k", "off"], stderr=subprocess.DEVNULL)
    except: pass

def ensure_jack_running():
    """Smart check: Only restart JACK if D-Bus is unresponsive or server is stopped."""
    print("Checking JACK D-Bus availability...")
    needs_restart = False
    reason = ""
    started_by_script = False
    
    try:
        # Check 1: Is the server started?
        status_output = subprocess.check_output(["jack_control", "status"], universal_newlines=True, timeout=5).lower()
        if "started" not in status_output:
            needs_restart = True
            reason = "Server is not reported as 'started'"
        else:
            # Check 2: Is the D-Bus interface actually responding?
            dbus_check = [
                "dbus-send", "--session", "--print-reply", 
                "--dest=org.jackaudio.service", "/org/jackaudio/Controller", 
                "org.jackaudio.JackControl.IsStarted"
            ]
            print(f"[DEBUG] Executing: {' '.join(dbus_check)}")
            subprocess.check_output(dbus_check, stderr=subprocess.STDOUT, universal_newlines=True, timeout=5)
            print("JACK D-Bus interface is active and healthy.")
    except Exception as e:
        needs_restart = True
        reason = str(e)

    if needs_restart:
        print(f"JACK needs attention: {reason}. Performing clean restart...")
        try:
            subprocess.run(["pkill", "-9", "jackd"], stderr=subprocess.DEVNULL)
            subprocess.run(["pkill", "-9", "jackdbus"], stderr=subprocess.DEVNULL)
            time.sleep(1)
            subprocess.run(["jack_control", "start"], check=True)
            time.sleep(3)
            print("JACK server started successfully.")
            started_by_script = True
        except Exception as e:
            print(f"Error restarting JACK: {e}")
            
    return started_by_script

def main():
    # 0. Ensure JACK is up and running
    jack_was_started_by_script = ensure_jack_running()

    # Capture the current terminal window ID so we can return to it later
    terminal_win_id = None
    try:
        output = subprocess.check_output(["xprop", "-root", "_NET_ACTIVE_WINDOW"], universal_newlines=True)
        terminal_win_id = output.split()[-1]
        print(f"Captured terminal window ID: {terminal_win_id}")
    except: pass

    print("Starting Dual Rocksmith Setup (D-Bus Strategy)...")

    # 1. Start D-Bus Listener FIRST (Silent Observer)
    listener = DbusJackListener()
    listener.start()

    # 2. Start alsa_in
    print(f"Starting alsa_in helper...")
    alsa_proc = subprocess.Popen(ALSA_CMD, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                                universal_newlines=True, bufsize=1)
    threading.Thread(target=monitor_alsa_output, args=(alsa_proc,), daemon=True).start()
    
    # Wait for alsa_in to establish itself in the JACK graph
    print("Waiting 3 seconds for audio bridge initialization...")
    time.sleep(3)

    # 3. Start Rocksmith Launcher (Detached)
    print(f"Launching Rocksmith...")
    try:
        subprocess.Popen([LAUNCHER_PATH], start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        print("Error: Launcher not found.")
        sys.exit(1)

    # 4. Wait for game to start
    print("Phase 1: Waiting for Rocksmith2014 process to appear...")
    while not check_rocksmith_process():
        time.sleep(1)
    
    # 5. D-Bus detection loop
    print("Phase 2: Waiting for JACK audio registration via D-Bus...")
    rs_audio_found = False
    start_wait = time.time()
    dbus_cmd_printed = False
    
    while not rs_audio_found:
        if time.time() - start_wait > 120:
            print("Warning: D-Bus detection timed out after 2m. Attempting blind connect.")
            break
            
        cmd = [
            "dbus-send", "--session", "--print-reply", 
            "--dest=org.jackaudio.service", "/org/jackaudio/Controller", 
            "org.jackaudio.JackPatchbay.GetGraph", "uint64:0"
        ]
        if not dbus_cmd_printed:
            print(f"[DEBUG] Executing: {' '.join(cmd)}")
            dbus_cmd_printed = True
            
        try:
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, universal_newlines=True)
            if "Rocksmith2014" in output:
                print("[DETECTED] Rocksmith2014 audio engine is live in JACK.")
                rs_audio_found = True
                break
        except: pass
        time.sleep(2)

    # 6. Stability and Connection
    print("Phase 3: Waiting 10 seconds for engine stabilization...")
    time.sleep(10)
    
    # Try to find Rocksmith window ID for precise return focus
    rocksmith_win_id = None
    try:
        rs_output = subprocess.check_output(["wmctrl", "-l"], universal_newlines=True)
        for line in rs_output.splitlines():
            if "Rocksmith 2014" in line:
                rocksmith_win_id = line.split()[0]
                print(f"Captured Rocksmith window ID: {rocksmith_win_id}")
                break
    except: pass
    
    connect_jack_ports(terminal_win_id, rocksmith_win_id)

    # 7. Monitor for exit
    print("Setup complete. Monitoring for game exit...")
    listener.stop()
    consecutive_missing = 0
    while True:
        if check_rocksmith_process():
            consecutive_missing = 0
        else:
            consecutive_missing += 1
            if consecutive_missing >= 10:
                print("Rocksmith closed. Cleaning up...")
                break
        time.sleep(1)

    # Cleanup
    alsa_proc.terminate()
    if jack_was_started_by_script:
        print("Shutting down JACK server started by this script...")
        try:
            subprocess.run(["jack_control", "stop"], stderr=subprocess.DEVNULL)
        except: pass

if __name__ == "__main__":
    main()