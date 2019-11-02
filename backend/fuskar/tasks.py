from __future__ import absolute_import
import os
import pickle
import time
from huey import crontab
from huey.contrib.djhuey import periodic_task, task, lock_task, enqueue
from django.conf import settings
from fuskar.models import Lecture, Student
from fuskar.utils.camera import get_frame
from fuskar.utils.helpers import get_id_from_enc, get_encodings
import face_recognition
from sklearn import svm


def get_boxes(frame):
    """
    Get boxes from a frame
    """
    # important conversion to rgb frame for dlib
    print("Converting frame to dlib format")
    rgb_frame = frame[:, :, ::-1]
    return frame, face_recognition.face_locations(rgb_frame, model='cnn')

@task()
@lock_task('retrain-pkl')
def retrain_pkl():
    """
    Background task for retraining the pickled objects
    """
    print("Triggered retraining embedding caches")
    encodings = []
    id_ = []

    
    # Training directory
    train_dir = os.listdir(settings.TRAIN_DIR)

    encoding_list_tuple = list()
    # Loop through each folder in the image directory
    for person in train_dir:
        person_folder = os.path.join(settings.TRAIN_DIR, person)
        person_folder_listing = os.listdir(person_folder)

        # Loop through each training image for the current person
        for image in person_folder_listing:
            # Get the face encodings for the face in each image file
            image_path = os.path.join(person_folder, image)
            face = face_recognition.load_image_file(image_path)
            try:
                boxes = face_recognition.face_locations(face, model='cnn')
                face_enc = face_recognition.face_encodings(face, known_face_locations=boxes)[0]
                # Add face encoding for current image with corresponding label (name) to the training data
                encodings.append(face_enc)
                id_.append(person)
                # create list of encodings tuples
                encoding_list_tuple.append((list(face_enc), person))
            except IndexError:
                pass
    if len(train_dir) > 1:
        # Create and train the SVC classifier
        settings.USE_EMBEDDING = True
        clf = svm.SVC(gamma='scale', probability=True)
        clf.fit(encodings, id_)
        with open(settings.SVM_EMBEDDING_MAP, 'wb') as output:
            print("Creating embedding map")
            pickle.dump(clf, output)
            print(f"Done creating embedding map at {settings.SVM_EMBEDDING_MAP}")
    else:
        print("Cannot create SVM with one class, switching to encoding mode")
        settings.USE_EMBEDDING = False
    with open(settings.ENCODING_LIST, 'wb') as output:
        print("Creating encoding list")
        pickle.dump(encoding_list_tuple, output)
        print(f"Done creating encoding list at {settings.ENCODING_LIST}")

# TODO: switch to batch_face_locations to process video stream at once for 
# quicker processing using nvidia speed up
@task()
def test_attendance(lecture_instance_id):
    """
    Begins taking attendance
    Once a Lecture object is created
    """
    if not Lecture.objects.get(id=lecture_instance_id).lock:
        print("##############################################################################")
        lecture_instance = Lecture.objects.get(id=lecture_instance_id)
        lecture_processing_time_start = time.time()
        frame_index = 0

        # retrieve classifier from the pickled embedding map
        if os.path.isfile(settings.SVM_EMBEDDING_MAP):
            with open(settings.SVM_EMBEDDING_MAP, 'rb') as stream:
                print("Loading Embedding Map for SVM-EMBEDDING mode")
                clf = pickle.load(stream)
                classes = clf.classes_
        else:
            print("Embedding Map cannot be found, Switching to FACE-ENCODING mode")
            settings.USE_EMBEDDING = False
        if not settings.USE_EMBEDDING:
            with open(settings.ENCODING_LIST, 'rb') as stream:
                print("Loading Encoding list for FACE-ENCODING mode")
                encoding_list_tuple = pickle.load(stream)

        while not Lecture.objects.get(id=lecture_instance_id).stopped_at:
            loop_processing_time_start = time.time()
            lecture_instance = Lecture.objects.get(id=lecture_instance_id)
            course = lecture_instance.course
            students = course.registered_students.all()
            print("Retrieving students ID")
            registered_student_ids = [int(student.id) for student in students]

            # video_stream is yielding all the images one by one
            _id = set({})
            # while True:
            frame = get_frame()
            frame, boxes = get_boxes(frame)
            print(f"Frame [{frame_index}] obtained from stream")
            # Find all the faces in the test image using the default HOG-based model
            # face_locations = face_recognition.face_locations(frame, number_of_times_to_upsample=3)
            no = len(boxes)
            print(f"Frame [{frame_index}]: {no} face(s) detected")
            
            # Get the embeddings of every face in the image
            embedding_list = [x for x in face_recognition.face_encodings(frame, known_face_locations=boxes)]
            # prediction output is a list of id 
            if settings.USE_EMBEDDING:
                # Prediction using SVM_EMBEDDING_MODE
                # Predict all the faces in the test image using the trained classifier
                prediction_set = set({})
                if len(embedding_list) > 0:
                    probability = list(clf.predict_proba(embedding_list))
                    for i in probability:
                        highest_probability =  max(i)
                        if highest_probability > settings.CONFIDENCE:
                            index = list(i).index(highest_probability)
                            prediction = classes[index]
                            prediction_set.add(prediction)
                        else:
                            print(f"Highest prob {round(highest_probability, 2)} is lower/equal confidence value {settings.CONFIDENCE}")
                    _id = _id.union(prediction_set)
            else:
                # Prediction using ENCODING_MODE
                encoding_list = get_encodings(encoding_list_tuple)
                if len(embedding_list) > 0:
                    for i in embedding_list:
                        results = face_recognition.face_distance(encoding_list, i)
                        # get minimum face distance and compare
                        min_distance = min(results)
                        index = list(results).index(min_distance)
                        if index:
                            encoding = encoding_list[index]
                            single_id = get_id_from_enc(encoding_list_tuple, encoding)
                            highest_probability = 1 - min_distance
                            if highest_probability > settings.CONFIDENCE:
                                _id.add(single_id)
                            else:
                                print(f"Highest prob {round(highest_probability, 4)} is lower/equal confidence value {settings.CONFIDENCE}")
            for i in _id:
                if int(i) in registered_student_ids:
                    # check lecture lock incase processing was occuring when lecture was stopped so as not to add 
                    # student after stopped_at
                    student = Student.objects.get(id=int(i))
                    lecture_instance.students_present.add(student)
                    print(f"Marking student with id {int(i)} as present for Lecture {lecture_instance.course.name}-{lecture_instance_id}")
                else:
                    print(f"Student {i} was recognized but was not registered for the course")

            frame_index = frame_index + 1
            print(f"Id's discovered in this iteration {_id}")
            print(f"Single frame processing ran in {round(time.time() - loop_processing_time_start, 1)} seconds")
            time.sleep(2)
        stop_lecture_time = time.time()
        print(f"Lecture {lecture_instance.course.name}-{lecture_instance.id} was stopped, exiting attendance, {frame_index} frame(s) processed")
        print(f"Lecture {lecture_instance.course.name}-{lecture_instance.id} attendance taking process ran for {round(stop_lecture_time - lecture_processing_time_start, 1)} seconds")
        print("##############################################################################")
