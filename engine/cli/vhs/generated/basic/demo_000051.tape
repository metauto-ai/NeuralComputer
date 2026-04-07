# ---- VHS documentation start (DO NOT CHANGE) ----
#
# Require:
#   Require <string>                Ensure a program is on the $PATH to proceed
#
# Sleep:
#   Sleep <time>                    Sleep for a set amount of <time> in seconds
#
# Type:
#   Type[@<time>] "<characters>"    Type <characters> into the terminal with a
#                                   <time> delay between each character
#
# Keys:
#   Escape[@<time>] [number]        Press the Escape key
#   Backspace[@<time>] [number]     Press the Backspace key
#   Delete[@<time>] [number]        Press the Delete key
#   Insert[@<time>] [number]        Press the Insert key
#   Down[@<time>] [number]          Press the Down key
#   Enter[@<time>] [number]         Press the Enter key
#   Space[@<time>] [number]         Press the Space key
#   Tab[@<time>] [number]           Press the Tab key
#   Left[@<time>] [number]          Press the Left Arrow key
#   Right[@<time>] [number]         Press the Right Arrow key
#   Up[@<time>] [number]            Press the Up Arrow key
#   Down[@<time>] [number]          Press the Down Arrow key
#   PageUp[@<time>] [number]        Press the Page Up key
#   PageDown[@<time>] [number]      Press the Page Down key
#   Ctrl+<key>                      Press the Control key + <key> (e.g. Ctrl+C)
#
# Display:
#   Hide                            Hide the subsequent commands from the output
#   Show                            Show the subsequent commands in the output
# ---- VHS documentation end (DO NOT CHANGE) ----

# ID: demo_000051
# INSTRUCTION: The demonstration runs `echo Current directory: $PWD` to label the working directory, keeping the focus on basic shell behaviour before hiding the prompt.
# CLASS: {"Basic": true, "Files": false, "Text": false, "Process": false, "Network": false, "Package": false, "VCS": false, "Build": false, "Users": false, "Admin": false, "FS": false, "Security": false, "DB": false, "Container": false, "Editors": false, "Exec": false, "Misc": false}
# LEVEL: 1
# INTERACTIVE: false
# EVENTS: 6
# VISUAL_COMPLEXITY: 16

# ---- Theme setting start (DO NOT CHANGE) ----
Output demo_000051.mp4


# "Catppuccin Mocha (Pure White, Warm Pink Cursor)"
Set Shell "bash"

Set Theme {
  "name": "Catppuccin Mocha (Pure White, Warm Pink Cursor)",
  "background": "#1e1e2e",
  "foreground": "#ffffff",
  "black": "#45475a",
  "red": "#f38ba8",
  "green": "#a6e3a1",
  "yellow": "#f9e2af",
  "blue": "#89b4fa",
  "purple": "#cba6f7",
  "cyan": "#94e2d5",
  "white": "#ffffff",
  "brightBlack": "#585b70",
  "brightRed": "#f38ba8",
  "brightGreen": "#a6e3a1",
  "brightYellow": "#f9e2af",
  "brightBlue": "#89b4fa",
  "brightPurple": "#cba6f7",
  "brightCyan": "#89dceb",
  "brightWhite": "#ffffff",
  "cursor": "#f5c2e7",
  "cursorAccent": "#1e1e2e",
  "selectionBackground": "#585b70"
}

Set FontSize 40
Set Width 1600
Set Height 900
Set TypingSpeed 70ms
Set PlaybackSpeed 1
Set Margin 28
Set MarginFill "#0091FF"
Set BorderRadius 25
Set Padding 18
Set LineHeight 1.2
Set LetterSpacing 0.8

# ---- Theme setting end (DO NOT CHANGE) ----

Sleep 180ms
Type "echo Current directory: $PWD"
Sleep 120ms
Enter
Sleep 400ms
Sleep 400ms
Hide
