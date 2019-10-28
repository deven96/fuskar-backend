import random
import string
import os
import cv2
import numpy as np
import imutils
import threading
from django.conf import settings

from fuskar.utils.nano import running_on_jetson_nano

if settings.DEBUG:
    media_path = settings.MEDIA_ROOT
    cache_path = settings.CACHE_ROOT
else:
    media_path = settings.MEDIA_URL
    cache_path = settings.CACHE_URL

video_camera = None
global_frame = None
prototxtfile = os.path.join(cache_path, "cache", "deploy.prototxt")
caffemodel = os.path.join(cache_path, "cache", "detect.caffemodel")
tempdir = os.path.join(media_path, "tempdir")
video_path = os.path.join(media_path, 'video', 'video.avi')

def randomString2(stringLength=8):
    """Generate a random string of fixed length """
    letters= string.ascii_lowercase
    return ''.join(random.sample(letters,stringLength))

def clear_temp():
    """
    Clear the tempdir
    """
    if os.path.exists(tempdir):
        for i in os.listdir(tempdir):
            os.remove(os.path.join(tempdir, i))
        os.remove(tempdir)
    print("Deleted temporary images")

class RecordingThread(threading.Thread):
    def __init__(self, name, camera):
        threading.Thread.__init__(self)
        self.name = name
        self.isRunning = True

        self.cap = camera
        fourcc = cv2.VideoWriter_fourcc(*'MJPG')
        self.out = cv2.VideoWriter(video_path,fourcc, 20.0, (640,480))

    def run(self):
        while self.isRunning:
            ret, frame = self.cap.read()
            if ret:
                self.out.write(frame)

        self.out.release()

    def stop(self):
        self.isRunning = False

    def __del__(self):
        self.out.release()

class VideoCamera(object):
    def __init__(self):
        # Open a camera
        if running_on_jetson_nano():
            self.cap = cv2.VideoCapture(
                # get_jetson_gstreamer_source(), 
                cv2.CAP_GSTREAMER
            )
        else:
            self.cap = cv2.VideoCapture(0)
      
        # Initialize video recording environment
        self.is_record = False
        self.out = None
        self.classifier = cv2.dnn.readNetFromCaffe(prototxtfile, caffemodel)

        # Thread for recording
        self.recordingThread = None
    
    def __del__(self):
        self.cap.release()
    
    def detect_face(self, frame, confidence=0.3, draw_bounding_box=True):
        """
        Detect a face from a frame and draw bounding box
        """
        frame = imutils.resize(frame, width=400)
     
        # grab the frame dimensions and convert it to a blob
        (h, w) = frame.shape[:2]
        blob = cv2.dnn.blobFromImage(cv2.resize(frame, (300, 300)), 1.0,
        (300, 300), (104.0, 177.0, 123.0))
        
        # pass the blob through the network and obtain the detections and
        # predictions
        self.classifier.setInput(blob)
        detections = self.classifier.forward()
        
        boxes = list()
        # loop over the detections
        for i in range(0, detections.shape[2]):
            # extract the confidence (i.e., probability) associated with the
            # prediction
            confidence_val = detections[0, 0, i, 2]
            
            # filter out weak detections by ensuring the `confidence` is
            # greater than the minimum confidence
            if confidence_val < confidence:
                continue
            
            # compute the (x, y)-coordinates of the bounding box for the
            # object
            box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
            (startX, startY, endX, endY) = box.astype("int")
            boxes.append((startX, startY, endX, endY))
            
            # draw the bounding box of the face along with the associated
            # probability
            text = "{:.2f}%".format(confidence * 100)
            y = startY - 10 if startY - 10 > 10 else startY + 10
            if draw_bounding_box:
                cv2.rectangle(frame, (startX, startY), (endX, endY),
                (0, 0, 255), 2)
                cv2.putText(frame, text, (startX, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 2)
        return frame, boxes

    def get_frame(self, ret_bytes=True, detect_face=True):
        """
        Get an individual frame

        :param ret_bytes: return as byte (default: True)
        :type ret_bytes: bool
        :param detect_face: draw bounding boxes on frame (default: True)
        :type detect_face: bool
        """
        ret, frame = self.cap.read()
        if detect_face:
            frame, boxes = self.detect_face(frame)
        if ret:
            ret, jpeg = cv2.imencode('.jpg', frame)
            if ret_bytes:
                # jpeg = cv2.imread("frame.jpeg")
                return jpeg.tobytes(), boxes
            else:
                return jpeg, boxes
        else:
            print("Could not read from camera")
            return None
        if not detect_face and frame:
            return frame

    def start_record(self):
        """
        Start recording a video
        """
        self.is_record = True
        self.recordingThread = RecordingThread("Video Recording Thread", self.cap)
        self.recordingThread.start()

    def stop_record(self):
        self.is_record = False

        if self.recordingThread != None:
            self.recordingThread.stop()


def video_stream():
    """
    Yield each frame to create the effect of a realtime video
    """
    global video_camera 
    global global_frame

    if video_camera == None:
        video_camera = VideoCamera()

    # if not, send StreamHTTPResponse formated responses (in bytes)
    print("Retrieving frame from camera as a stream [bytes mode]")
    while True:
        frame, _ = video_camera.get_frame()
        if frame != None:
            global_frame = frame
            yield (b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')
        else:
            yield (b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n\r\n' + global_frame + b'\r\n\r\n')

def get_frame():
    """
    Retrieve a single frame from the camera
    """
    global video_camera

    if video_camera == None:
        video_camera = VideoCamera()
    frame = video_camera.get_frame(ret_bytes=False, detect_face=False)
    print("Retrieving frame from camera as a picture [jpeg mode]")
    return frame

def stop_cam():
    """
    Stop global camera object thread
    """
    global video_camera

    if video_camera:
        video_camera.stop_record()

def capture_from_camera(student_id, number=10):
    """
    Run the student capture process
    """
    global video_camera

    if video_camera == None:
        video_camera = VideoCamera()
    print(f"Taking pictures for student {student_id}")
    video_camera.take_pictures(student_id=student_id, number=number)
    video_camera.stop_record()