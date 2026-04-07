#!/bin/bash
rm -f /tmp/.X${DISPLAY_NUM}-lock
rm -f /tmp/.X11-unix/X${DISPLAY_NUM}

mkdir -p $HOME/.config/xfce4/xfconf/xfce-perchannel-xml
mkdir -p $HOME/.config/xfce4/desktop
mkdir -p $HOME/Desktop

WALLPAPER_PATH="${WALLPAPER_PATH:-/usr/share/backgrounds/xfce/background.png}"
if [ ! -f "$WALLPAPER_PATH" ]; then
  WALLPAPER_PATH="/usr/share/backgrounds/xfce/background.png"
fi

CURSOR_THEME="${CURSOR_THEME:-Adwaita}"
CURSOR_SIZE="${CURSOR_SIZE:-40}"
export XCURSOR_THEME="$CURSOR_THEME"
export XCURSOR_SIZE="$CURSOR_SIZE"

UI_FONT_SIZE="${UI_FONT_SIZE:-13}"
DESKTOP_ICON_SIZE="${DESKTOP_ICON_SIZE:-96}"
VSCODE_ZOOM="${VSCODE_ZOOM:-1}"
VSCODE_FONT_SIZE="${VSCODE_FONT_SIZE:-18}"
VSCODE_TERMINAL_FONT_SIZE="${VSCODE_TERMINAL_FONT_SIZE:-16}"

mkdir -p $HOME/Documents
mkdir -p $HOME/Downloads
mkdir -p $HOME/Pictures
mkdir -p $HOME/Music
mkdir -p $HOME/Videos
mkdir -p $HOME/workspace

cp /usr/share/backgrounds/xfce/icons.screen.latest.rc $HOME/.config/xfce4/desktop/

find "$HOME/Desktop" -maxdepth 1 -type f -name "*.desktop" -delete

cat <<'EOF' > $HOME/Desktop/firefox.desktop
[Desktop Entry]
Type=Application
Name=Firefox
Exec=/usr/bin/firefox-esr
TryExec=/usr/bin/firefox-esr
Icon=firefox
Terminal=false
Categories=Network;WebBrowser;
EOF
chmod +x $HOME/Desktop/firefox.desktop

cat <<'EOF' > $HOME/Desktop/gimp.desktop
[Desktop Entry]
Type=Application
Name=GIMP
Exec=gimp
TryExec=gimp
Icon=gimp
Terminal=false
Categories=Graphics;ImageEditor;
EOF
chmod +x $HOME/Desktop/gimp.desktop

cat <<'EOF' > $HOME/Desktop/files.desktop
[Desktop Entry]
Type=Application
Name=Files
Exec=nautilus --new-window
TryExec=nautilus
Icon=org.gnome.Nautilus
Terminal=false
Categories=Utility;FileManager;
EOF
chmod +x $HOME/Desktop/files.desktop

cat <<'EOF' > $HOME/Desktop/mahjongg.desktop
[Desktop Entry]
Type=Application
Name=Mahjongg
Exec=gnome-mahjongg
TryExec=gnome-mahjongg
Icon=org.gnome.Mahjongg
Terminal=false
Categories=Game;
EOF
chmod +x $HOME/Desktop/mahjongg.desktop

cat <<'EOF' > $HOME/Desktop/term.desktop
[Desktop Entry]
Type=Application
Name=Term
Exec=xfce4-terminal
TryExec=xfce4-terminal
Icon=utilities-terminal
Terminal=false
Categories=System;TerminalEmulator;
EOF
chmod +x $HOME/Desktop/term.desktop

cat <<'EOF' > $HOME/Desktop/calc.desktop
[Desktop Entry]
Type=Application
Name=Calc
Exec=gnome-calculator
TryExec=gnome-calculator
Icon=accessories-calculator
Terminal=false
Categories=Utility;Calculator;
EOF
chmod +x $HOME/Desktop/calc.desktop

cat <<'EOF' > $HOME/Desktop/vscode.desktop
[Desktop Entry]
Type=Application
Name=VS Code
Exec=code
TryExec=code
Icon=code
Terminal=false
Categories=Development;IDE;
EOF
chmod +x $HOME/Desktop/vscode.desktop

cat <<'EOF' > $HOME/Desktop/vlc.desktop
[Desktop Entry]
Type=Application
Name=VLC
Exec=vlc
TryExec=vlc
Icon=vlc
Terminal=false
Categories=AudioVideo;Player;
EOF
chmod +x $HOME/Desktop/vlc.desktop

mkdir -p "$HOME/.config/Code/User"
cat <<EOF > "$HOME/.config/Code/User/settings.json"
{
  "window.zoomLevel": ${VSCODE_ZOOM},
  "editor.fontSize": ${VSCODE_FONT_SIZE},
  "terminal.integrated.fontSize": ${VSCODE_TERMINAL_FONT_SIZE}
}
EOF

mkdir -p $HOME/.config/gtk-3.0
cat <<EOF > $HOME/.config/gtk-3.0/settings.ini
[Settings]
gtk-theme-name=Arc-Dark
gtk-icon-theme-name=Papirus
gtk-font-name=Sans ${UI_FONT_SIZE}
gtk-cursor-theme-name=${CURSOR_THEME}
gtk-cursor-theme-size=${CURSOR_SIZE}
gtk-toolbar-style=GTK_TOOLBAR_BOTH_HORIZ
gtk-menu-images=1
gtk-button-images=1
gtk-enable-event-sounds=1
gtk-enable-input-feedback-sounds=1
gtk-xft-antialias=1
gtk-xft-hinting=1
gtk-xft-hintstyle=hintfull
EOF

mkdir -p $HOME/.config/gtk-2.0
cat <<EOF > $HOME/.config/gtk-2.0/gtkrc
gtk-theme-name = "Arc-Dark"
gtk-icon-theme-name = "Papirus"
gtk-font-name = "Sans ${UI_FONT_SIZE}"
gtk-cursor-theme-name = "${CURSOR_THEME}"
gtk-cursor-theme-size = ${CURSOR_SIZE}
gtk-toolbar-style = GTK_TOOLBAR_BOTH_HORIZ
gtk-menu-images = 1
gtk-button-images = 1
EOF

mkdir -p $HOME/.config/xfce4/xfconf/xfce-perchannel-xml
cat <<EOF > $HOME/.config/xfce4/xfconf/xfce-perchannel-xml/xsettings.xml
<?xml version="1.0" encoding="UTF-8"?>
<channel name="xsettings" version="1.0">
  <property name="Net" type="empty">
    <property name="ThemeName" type="string" value="Arc-Dark"/>
    <property name="IconThemeName" type="string" value="Papirus"/>
    <property name="CursorThemeName" type="string" value="${CURSOR_THEME}"/>
    <property name="CursorThemeSize" type="int" value="${CURSOR_SIZE}"/>
    <property name="DoubleClickTime" type="int" value="400"/>
    <property name="DoubleClickDistance" type="int" value="5"/>
    <property name="DndDragThreshold" type="int" value="8"/>
    <property name="CursorBlink" type="bool" value="true"/>
    <property name="CursorBlinkTime" type="int" value="1200"/>
    <property name="SoundThemeName" type="string" value="default"/>
    <property name="EnableEventSounds" type="bool" value="true"/>
    <property name="EnableInputFeedbackSounds" type="bool" value="true"/>
  </property>
  <property name="Xft" type="empty">
    <property name="DPI" type="empty"/>
    <property name="Antialias" type="int" value="-1"/>
    <property name="Hinting" type="int" value="-1"/>
    <property name="HintStyle" type="string" value="hintfull"/>
    <property name="RGBA" type="string" value="rgb"/>
  </property>
  <property name="Gtk" type="empty">
    <property name="ColorPalette" type="string" value="black:white:gray50:red:purple:blue:light blue:green:yellow:orange:lavender:brown:goldenrod4:dodger blue:pink:light green:gray10:gray30:gray75:gray90"/>
    <property name="FontName" type="string" value="Sans ${UI_FONT_SIZE}"/>
    <property name="MenuBarAccel" type="string" value="F10"/>
    <property name="CanChangeAccels" type="bool" value="false"/>
    <property name="MenuImages" type="bool" value="true"/>
    <property name="ButtonImages" type="bool" value="true"/>
    <property name="ToolbarStyle" type="string" value="GTK_TOOLBAR_BOTH_HORIZ"/>
    <property name="ToolbarIconSize" type="string" value="GTK_ICON_SIZE_LARGE_TOOLBAR"/>
    <property name="PrimaryButtonWarpsSlider" type="bool" value="false"/>
    <property name="ShowInputMethodMenu" type="bool" value="true"/>
    <property name="ShowUnicodeMenu" type="bool" value="true"/>
    <property name="AutoMnemonics" type="bool" value="true"/>
    <property name="RecentFilesEnabled" type="bool" value="true"/>
    <property name="RecentFilesMaxAge" type="int" value="30"/>
    <property name="RecentFilesMaxItems" type="int" value="10"/>
    <property name="ImModule" type="string" value=""/>
    <property name="ImPreeditStyle" type="string" value=""/>
    <property name="ImStatusStyle" type="string" value=""/>
    <property name="ShellShowsAppMenu" type="bool" value="false"/>
    <property name="ShellShowsMenubar" type="bool" value="true"/>
    <property name="DecorationLayout" type="string" value="menu:minimize,maximize,close"/>
    <property name="TitlebarUsesSystemFont" type="bool" value="false"/>
    <property name="TitlebarDoubleClick" type="string" value="toggle-maximize"/>
    <property name="TitlebarMiddleClick" type="string" value="none"/>
    <property name="TitlebarRightClick" type="string" value="menu"/>
    <property name="DialogsUseHeader" type="bool" value="false"/>
    <property name="EnablePrimaryPaste" type="bool" value="true"/>
    <property name="RecentFilesLimit" type="int" value="20"/>
    <property name="ColorScheme" type="string" value=""/>
  </property>
</channel>
EOF

cat <<EOF > $HOME/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-desktop.xml
<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfce4-desktop" version="1.0">
  <property name="backdrop" type="empty">
    <property name="screen0" type="empty">
      <property name="monitor0" type="empty">
        <property name="workspace0" type="empty">
          <property name="last-image" type="string" value="${WALLPAPER_PATH}"/>
          <property name="image-style" type="int" value="5"/>
        </property>
      </property>
      <property name="monitorscreen" type="empty">
        <property name="workspace0" type="empty">
          <property name="last-image" type="string" value="${WALLPAPER_PATH}"/>
          <property name="image-style" type="int" value="5"/>
        </property>
        <property name="workspace1" type="empty">
          <property name="last-image" type="string" value="${WALLPAPER_PATH}"/>
          <property name="image-style" type="int" value="5"/>
        </property>
        <property name="workspace2" type="empty">
          <property name="last-image" type="string" value="${WALLPAPER_PATH}"/>
          <property name="image-style" type="int" value="5"/>
        </property>
        <property name="workspace3" type="empty">
          <property name="last-image" type="string" value="${WALLPAPER_PATH}"/>
          <property name="image-style" type="int" value="5"/>
        </property>
      </property>
    </property>
  </property>
  <property name="desktop-icons" type="empty">
    <property name="style" type="int" value="2"/>
    <property name="icon-size" type="int" value="${DESKTOP_ICON_SIZE}"/>
    <property name="file-icons" type="empty">
      <property name="show-home" type="bool" value="true"/>
      <property name="show-filesystem" type="bool" value="true"/>
      <property name="show-trash" type="bool" value="true"/>
      <property name="show-removable" type="bool" value="false"/>
    </property>
  </property>
</channel>
EOF

cat <<EOF > $HOME/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-panel.xml
<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfce4-panel" version="1.0">
  <property name="configver" type="int" value="2"/>
  <property name="panels" type="array">
    <value type="int" value="2" />
      <property name="panel-2" type="empty">
        <property name="plugin-ids" type="array">
        </property>
        <property name="position" type="string" value="p=0;x=4096;y=4096" />
        <property name="size" type="uint" value="0" />
      </property>
  </property>
  <property name="plugins" type="empty">
  </property>
</channel>
EOF

cat <<EOF > $HOME/.config/xfce4/xfconf/xfce-perchannel-xml/xfwm4.xml
<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfwm4" version="1.0">
  <property name="general" type="empty">
    <property name="theme" type="string" value="Arc-Dark"/>
    <property name="double_click_action" type="string" value="maximize"/>
    <property name="double_click_distance" type="int" value="5"/>
    <property name="double_click_time" type="int" value="250"/>
    <property name="wrap_cycle" type="bool" value="true"/>
    <property name="wrap_layout" type="bool" value="true"/>
    <property name="wrap_resistance" type="int" value="10"/>
    <property name="wrap_windows" type="bool" value="true"/>
    <property name="wrap_workspaces" type="bool" value="false"/>
    <property name="click_to_focus" type="bool" value="true"/>
    <property name="focus_delay" type="int" value="200"/>
    <property name="cycle_apps_only" type="bool" value="false"/>
    <property name="cycle_draw_frame" type="bool" value="true"/>
    <property name="cycle_hidden" type="bool" value="true"/>
    <property name="cycle_minimized" type="bool" value="true"/>
    <property name="cycle_minimized_alt_tab" type="bool" value="true"/>
    <property name="cycle_workspaces" type="bool" value="false"/>
    <property name="raise_on_click" type="bool" value="true"/>
    <property name="raise_on_focus" type="bool" value="false"/>
    <property name="raise_with_any_button" type="bool" value="true"/>
    <property name="mousewheel_rollup" type="bool" value="true"/>
    <property name="prevent_focus_stealing" type="bool" value="false"/>
    <property name="activate_action" type="string" value="bring"/>
    <property name="borderless_maximize" type="bool" value="false"/>
    <property name="box_move" type="bool" value="false"/>
    <property name="box_resize" type="bool" value="false"/>
    <property name="easy_click" type="string" value="Mod4"/>
    <property name="initiate_window_move" type="string" value="Alt"/>
    <property name="initiate_window_resize" type="string" value="Alt"/>
    <property name="keyboard_focus" type="string" value="Alt"/>
    <property name="maximize_window_key" type="string" value="Alt"/>
    <property name="show_dock_shadow" type="bool" value="true"/>
    <property name="show_popup_shadow" type="bool" value="true"/>
    <property name="show_frame_shadow" type="bool" value="true"/>
    <property name="show_dock_shadow" type="bool" value="true"/>
    <property name="show_popup_shadow" type="bool" value="true"/>
    <property name="show_frame_shadow" type="bool" value="true"/>
    <property name="show_app_shadow" type="bool" value="true"/>
    <property name="shadow_delta_height" type="int" value="0"/>
    <property name="shadow_delta_width" type="int" value="0"/>
    <property name="shadow_delta_x" type="int" value="0"/>
    <property name="shadow_delta_y" type="int" value="0"/>
    <property name="shadow_opacity" type="int" value="50"/>
    <property name="sync_to_vblank" type="bool" value="false"/>
    <property name="tile_on_move" type="bool" value="true"/>
    <property name="title_alignment" type="string" value="center"/>
    <property name="title_font" type="string" value="Sans Bold 12"/>
    <property name="title_horizontal_offset" type="int" value="0"/>
    <property name="title_shadow_active" type="string" value="false"/>
    <property name="title_shadow_inactive" type="string" value="false"/>
    <property name="title_vertical_offset_active" type="int" value="0"/>
    <property name="title_vertical_offset_inactive" type="int" value="0"/>
    <property name="toggle_workspaces" type="string" value="disabled"/>
    <property name="unresponsive_drag" type="bool" value="true"/>
    <property name="use_compositing" type="bool" value="true"/>
    <property name="workspace_count" type="int" value="4"/>
    <property name="workspace_names" type="array">
      <value type="string" value="Workspace 1"/>
      <value type="string" value="Workspace 2"/>
      <value type="string" value="Workspace 3"/>
      <value type="string" value="Workspace 4"/>
    </property>
    <property name="wrap_windows" type="bool" value="true"/>
    <property name="wrap_workspaces" type="bool" value="false"/>
    <property name="zoom_desktop" type="bool" value="true"/>
    <property name="zoom_desktop_maximize" type="bool" value="true"/>
  </property>
</channel>
EOF

echo "Starting Xvfb..."
Xvfb :${DISPLAY_NUM} -screen 0 ${SCREEN_WIDTH}x${SCREEN_HEIGHT}x${SCREEN_DEPTH} &
sleep 2
XVFB_PID=$!

echo "Waiting for X server to start..."
for i in $(seq 1 10); do
    if xdpyinfo >/dev/null 2>&1; then
        echo "X server is ready"
        break
    fi
    sleep 1
done

export DISPLAY=:${DISPLAY_NUM}
echo "DISPLAY environment variable set to: $DISPLAY"

export GTK_THEME=Arc-Dark
export ICON_THEME=Papirus
export XDG_CURRENT_DESKTOP=XFCE

echo "Starting XFCE4 desktop environment..."
startxfce4 &
sleep 5
xfce4-panel --quit
sleep 1

xfconf-query -c xsettings -p /Net/ThemeName -s "Arc-Dark" || true
xfconf-query -c xsettings -p /Net/IconThemeName -s "Papirus" || true
xfconf-query -c xfwm4 -p /general/theme -s "Arc-Dark" || true
xfconf-query -c xsettings -p /Gtk/CursorThemeName -s "${CURSOR_THEME}" || true
xfconf-query -c xsettings -p /Gtk/CursorThemeSize -t int -s "${CURSOR_SIZE}" || true
xfconf-query -c xsettings -p /Net/CursorThemeName -s "${CURSOR_THEME}" || true
xfconf-query -c xsettings -p /Net/CursorThemeSize -t int -s "${CURSOR_SIZE}" || true
xfconf-query -c xsettings -p /Gtk/FontName -s "Sans ${UI_FONT_SIZE}" || true
xfconf-query -c xfwm4 -p /general/title_font -s "Sans Bold 12" || true
xfconf-query -c xfce4-desktop -p /desktop-icons/style -t int -s 2 --create || true
xfconf-query -c xfce4-desktop -p /desktop-icons/icon-size -t int -s "${DESKTOP_ICON_SIZE}" --create || true
xfconf-query -c xfce4-desktop -p /desktop-icons/file-icons/show-home -t bool -s true --create || true
xfconf-query -c xfce4-desktop -p /desktop-icons/file-icons/show-filesystem -t bool -s true --create || true
xfconf-query -c xfce4-desktop -p /desktop-icons/file-icons/show-trash -t bool -s true --create || true
xfconf-query -c xfce4-desktop -p /desktop-icons/file-icons/show-removable -t bool -s false --create || true

xfdesktop --reload || true

xfsettingsd --replace &
xfwm4 --replace &
sleep 2

echo "Starting VNC server..."
x11vnc -display :${DISPLAY_NUM} -passwd vncpassword -forever -nopw -listen 0.0.0.0 -rfbport 5900 &

echo "Starting noVNC proxy..."
/opt/noVNC/utils/novnc_proxy --vnc localhost:5900 --listen 6080 &

export PATH="/opt/conda/bin:$PATH"
mkdir -p $HOME/workspace
echo "Desktop ready on :${DISPLAY_NUM}"
echo "VNC: 5900"
echo "noVNC: 6080"

wait $XVFB_PID
