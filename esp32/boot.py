# boot.py runs on every board startup.
# It enables WebREPL so remote editing over WiFi is available.

try:
    import webrepl
    webrepl.start()
    print("WebREPL: enabled")
except Exception as exc:
    print("WebREPL: not enabled - run webrepl_setup first:", exc)
