import platform

def running_on_jetson_nano():
    return platform.machine() == "aarch64"