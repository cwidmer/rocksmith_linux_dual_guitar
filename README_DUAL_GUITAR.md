# Rocksmith 2014 Dual Guitar Setup on Linux (openSUSE)

This guide documents the successful configuration of Rocksmith 2014 with **two Real Tone Cables** on openSUSE Leap 15.6, using Proton 8.0, JACK, WineASIO, and RS_ASIO.

## 1. Prerequisites

*   **OS:** openSUSE Leap 15.6 (or similar Linux distro)
*   **Game:** Rocksmith 2014 Remastered (Steam)
*   **Compatibility Tool:** Proton 8.0
*   **Audio Hardware:** Two Official Real Tone Cables (RTC)
*   **System Packages:** `jackd`, `qjackctl`, `wineasio`, `alsa-utils` (for `alsa_in`), `python3-psutil`, `wmctrl`, `xprop`.
*   **User Groups:** User must be in the `audio` group (`sudo usermod -aG audio $USER`).

## 2. Core Components Installation

### A. RS_ASIO Mod
1.  Download the latest `RS_ASIO` release (DLLs).
2.  Place the DLLs (`avrt.dll`, `d3d9.dll`, etc.) in the Rocksmith 2014 root folder:
    `/home/chris/.local/share/Steam/steamapps/common/Rocksmith2014/`

### B. WineASIO Setup
1.  **Install WineASIO:** Ensure `wineasio` is installed via your package manager or built from source.
2.  **Copy DLLs to Proton:** Manually copy the `wineasio.dll.so` files to the Proton version used by the game (e.g., `Proton 8.0/dist/lib/wine/i386-unix/`).
3.  **Register WineASIO:** Run `regsvr32 wineasio.dll` inside the Rocksmith Wine prefix.
4.  **Configure Registry:** In `regedit`, set `HKEY_CURRENT_USER\Software\Wine\WineASIO\Number of inputs` to `2` (or higher, e.g., `16`).

## 3. Configuration Files

### A. Rocksmith Launcher Script (`rocksmith-launcher.sh`)
**Crucial:** Add `wineasio=n,b;` to the `WINEDLLOVERRIDES` variable.

### B. RS_ASIO.ini
*   `EnableWasapiInputs=0`: **Required** to bypass native cable detection.
*   `Driver=wineasio-rsasio`: The specific driver name for this system.
*   `[Asio.Input.0]` -> `Channel=0` (Player 1)
*   `[Asio.Input.1]` -> `Channel=1` (Player 2)

### C. Rocksmith.ini (Visual Fixes)
*   Hardcode `ScreenWidth` and `ScreenHeight` to your monitor's resolution.
*   Set `Fullscreen=2` (Windowed Fullscreen) or `0` (Windowed) to prevent Player 2 UI invisibility.

## 4. The Dual Guitar Automation Script (Recommended)

The Python script `dual_rocksmith.py` provides full, crash-safe automation by combining D-Bus monitoring with window focus management.

**Usage:**
```bash
./dual_rocksmith.py
```

**What the script does:**
1.  **Auto-manages JACK:** Checks if JACK is running with D-Bus support. Starts it if stopped, and shuts it down on exit if the script started it.
2.  **Audio Bridge:** Starts `alsa_in` for the second guitar *before* launching the game.
3.  **Launches Game:** Starts Rocksmith in a detached session.
4.  **D-Bus Monitoring:** Uses non-intrusive D-Bus queries to detect when Rocksmith's audio engine is live. This avoids the "Client Noise" crashes caused by polling.
5.  **Focus Automation:** Automatically captures your terminal ID and the Rocksmith window ID to perform the necessary "Alt-Tab" workaround for connection stability.
6.  **Auto-Connect:** Automatically connects `RTC_2:capture_1` to `Rocksmith2014:in_2` after a 10s stabilization delay.
7.  **Robust Cleanup:** Monitors the game process and shuts down the audio bridge when the game exits.

## 5. Manual Setup Procedure

If automation fails, use this verified sequence:
1.  **Check Cards:** `cat /proc/asound/cards` (Identify Playback card vs Cables).
2.  **Configure JACK:** In Qjackctl Setup, set **Interface** to your playback card (e.g., `hw:PCH`).
3.  **Start Helper:** `alsa_in -j "RTC_2" -d hw:Adapter_1 -r 48000 -c 1`.
4.  **Launch Game:** Start Rocksmith.
5.  **Alt-Tab & Connect:** Alt-Tab out at the "Red Screen" (initial logos) and use Qjackctl to connect `RTC_2:capture_1` -> `Rocksmith2014:in_2`.

## 6. Troubleshooting

*   **Invisible UI/Notes:** Hardcode resolution in `Rocksmith.ini`.
*   **No Sound Output:** Verify JACK is using the correct card (e.g., `hw:PCH` instead of `hw:0`).
*   **Alsa error (-11):** Script will report this if the USB cable loses sync. Restart the script.
*   **Stability Tip:** Always Alt-Tab during the initial logos ("Red Screen") if doing it manually.
