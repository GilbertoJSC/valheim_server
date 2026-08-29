@echo off
set SteamAppId=892970
echo "Starting Valheim server - PRESS CTRL-C to exit"

REM Tip: This is a COPY of start_headless_server.bat so Steam updates don't overwrite your settings.
REM NOTE: Minimum password length is 5 characters & password cant be in the server name.
REM NOTE: Open UDP ports 2456-2458 on this machine's firewall (LAN only, no router port forwarding needed).

valheim_server -nographics -batchmode ^
  -name "ValheimServer" ^
  -port 2456 ^
  -world "Dedicated" ^
  -password "ChangeMe123" ^
  -public 0
