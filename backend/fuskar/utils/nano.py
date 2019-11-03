import platform

def running_on_jetson_nano():
    return platform.machine() == "aarch64"


def get_jetson_gstreamer_source(capture_width=1280, capture_height=720, display_width=1280, display_height=720, framerate=60, flip_method=0):
    """
    Return an OpenCV-compatible video source description that uses gstreamer to capture video from the camera on a Jetson Nano
    """
    return (
            f'nvarguscamerasrc ! video/x-raw(memory:NVMM), ' +
            f'width=(int){capture_width}, height=(int){capture_height}, ' +
            f'format=(string)NV12, framerate=(fraction){framerate}/1 ! ' +
            f'nvvidconv flip-method={flip_method} ! ' +
            f'video/x-raw, width=(int){display_width}, height=(int){display_height}, format=(string)BGRx ! ' +
            'videoconvert ! video/x-raw, format=(string)BGR ! appsink'
            )