import signal


def handle_SIGINT(sig, frame):
    """
    Handle CTRL-C quit by setting run flag to false
    This will break out of main loop and let you close
    pixy gracefully
    """
    global run_flag
    run_flag = False


def setup():
    """
    Set Ctrl+C to switch run_flag to False rather than drop out entirely.    
    """
    signal.signal(signal.SIGINT, handle_SIGINT)