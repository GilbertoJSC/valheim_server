#!/bin/bash
# Copy of start_server.sh so Steam updates don't overwrite your settings.
# Make executable: chmod +x start_server.sh

export SteamAppId=892970

./valheim_server.x86_64 -nographics -batchmode \
  -name "ValheimServer" \
  -port 2456 \
  -world "Dedicated" \
  -password "ChangeMe123" \
  -public 0
