#!/bin/bash
#Run game or given command in environment

cd "/home/chris/.local/share/Steam/steamapps/common/Rocksmith2014"
DEF_CMD=("/home/chris/.local/share/Steam/steamapps/common/Rocksmith2014/Rocksmith2014.exe" "-uplay_steam_mode")
PATH="/home/chris/.local/share/Steam/steamapps/common/Proton 8.0/dist/bin/:/usr/bin:/bin" \
	TERM="xterm" \
	WINEDEBUG="-all" \
	WINEDLLPATH="/home/chris/.local/share/Steam/steamapps/common/Proton 8.0/dist/lib64//wine:/home/chris/.local/share/Steam/steamapps/common/Proton 8.0/dist/lib//wine" \
	LD_LIBRARY_PATH="/home/chris/.local/share/Steam/ubuntu12_64/video/:/home/chris/.local/share/Steam/ubuntu12_32/video/:/home/chris/.local/share/Steam/steamapps/common/Proton 8.0/dist/lib64/:/home/chris/.local/share/Steam/steamapps/common/Proton 8.0/dist/lib/:/usr/lib/pressure-vessel/overrides/lib/x86_64-linux-gnu/aliases:/usr/lib/pressure-vessel/overrides/lib/i386-linux-gnu/aliases" \
	WINEPREFIX="/home/chris/.local/share/Steam/steamapps/compatdata/221680/pfx/" \
	WINEESYNC="1" \
	WINEFSYNC="1" \
	SteamGameId="221680" \
	SteamAppId="221680" \
	WINEDLLOVERRIDES="steam.exe=b;dotnetfx35.exe=b;dotnetfx35setup.exe=b;beclient.dll=b,n;beclient_x64.dll=b,n;d3d11=n;d3d10core=n;d3d9=n;dxgi=n;d3d12=n;d3d12core=n" \
	STEAM_COMPAT_CLIENT_INSTALL_PATH="/home/chris/.local/share/Steam" \
	WINE_LARGE_ADDRESS_AWARE="1" \
	GST_PLUGIN_SYSTEM_PATH_1_0="/home/chris/.local/share/Steam/steamapps/common/Proton 8.0/dist/lib64/gstreamer-1.0:/home/chris/.local/share/Steam/steamapps/common/Proton 8.0/dist/lib/gstreamer-1.0" \
	WINE_GST_REGISTRY_DIR="/home/chris/.local/share/Steam/steamapps/compatdata/221680/gstreamer-1.0/" \
	MEDIACONV_AUDIO_DUMP_FILE="/home/chris/.local/share/Steam/steamapps/shadercache/221680/fozmediav1/audiov2.foz" \
	MEDIACONV_AUDIO_TRANSCODED_FILE="/home/chris/.local/share/Steam/steamapps/shadercache/221680/transcoded_audio.foz" \
	MEDIACONV_VIDEO_DUMP_FILE="/home/chris/.local/share/Steam/steamapps/shadercache/221680/fozmediav1/video.foz" \
	MEDIACONV_VIDEO_TRANSCODED_FILE="/home/chris/.local/share/Steam/steamapps/shadercache/221680/transcoded_video.foz" \
	"/home/chris/.local/share/Steam/steamapps/common/Proton 8.0/dist/bin/wine64" c:\\windows\\system32\\steam.exe "${@:-${DEF_CMD[@]}}"
