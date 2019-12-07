from __future__ import absolute_import
import os
import cv2
import time
import pickle
import numpy as np
from huey import crontab
from django.conf import settings
from django.db.utils import OperationalError
from huey.contrib.djhuey import periodic_task, task, lock_task, enqueue
from fuskar.models import Lecture, Student
from fuskar.artificial import classifiers as cf
from fuskar.utils.camera import get_frame
import face_recognition


def get_boxes(frame):
    """
    Get boxes from a frame
    """
    # important conversion to rgb frame for dlib
    print("Converting frame to dlib format")
    rgb_frame = frame[:, :, ::-1]
    return frame, face_recognition.face_locations(rgb_frame, model='cnn')

@task()
@lock_task('rm-image-objects')
def remove_image_objects(image_instance):
    """
    Removes the hardcopy of an image and removes it from the cached resources
    """
    print(f"Received command to remove all cached instances of {image_instance.file.path}")
    # remove it from path-to-embedding dict
    if os.path.isfile(settings.PATH_TO_EMBEDDING_DICT):
        with open(settings.PATH_TO_EMBEDDING_DICT, 'rb') as stream:
                path_to_embed_dict = pickle.load(stream)
        if image_instance.file.path in path_to_embed_dict.keys():
            del path_to_embed_dict[image_instance.file.path]
            print(f"Deleted Embeddings from Path to Embedding cache")
        with open(settings.PATH_TO_EMBEDDING_DICT, 'wb') as stream:
            pickle.dump(path_to_embed_dict, stream)
    # retrain pkl to remove image from svm map and serial encodings
    retrain_pkl()


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

    if os.path.exists(settings.PATH_TO_EMBEDDING_DICT):
        with open(settings.PATH_TO_EMBEDDING_DICT, 'rb') as stream:
            path_to_embed_dict = pickle.load(stream)
    else:
        path_to_embed_dict = dict()

    encoding_list_tuple = list()
    # Loop through each folder in the image directory
    for person in train_dir:
        person_folder = os.path.join(settings.TRAIN_DIR, person)
        person_folder_listing = os.listdir(person_folder)

        # Loop through each training image for the current person
        for image in person_folder_listing:
            # Get the face encodings for the face in each image file
            image_path = os.path.join(person_folder, image)
            if image_path in path_to_embed_dict.keys():
                face_enc = path_to_embed_dict[image_path]
                id_.append(person)
                encodings.append(face_enc)
                encoding_list_tuple.append((list(face_enc), person))
            else:
                print(f"Image at {image_path} is not in cache, adding to path-to-embed-dict")
                face = face_recognition.load_image_file(image_path)
                boxes = face_recognition.face_locations(face, model='cnn')
                try:
                    face_enc = face_recognition.face_encodings(face, known_face_locations=boxes)[0]
                    # Add face encoding for current image with corresponding label (name) to the training data
                    encodings.append(face_enc)
                    id_.append(person)
                    # create list of encodings tuples
                    encoding_list_tuple.append((list(face_enc), person))
                    # add it to path-to-embed-dict
                    path_to_embed_dict[image_path] = face_enc
                except IndexError:
                    pass
        
    
    if len(train_dir) > 1:
        # Create and train the classifiers
        settings.PREDICTION_MODE = "knn"
        cf.SVM.train(X=encodings, Y=id_, pickle_path=settings.SVM_EMBEDDING_MAP)
        cf.KNN.train(X=encodings, Y=id_, pickle_path=settings.KNN_EMBEDDING_MAP)
    else:
        # use direct euclid if only one student is registered
        settings.PREDICTION_MODE = "direct-euclid"
        cf.DirectEuclid.train(pickle_path=settings.ENCODING_LIST, encoding_list_tuple=encoding_list_tuple)
    
    # This dictionary helps prevent scrolling over the entire folder of images recomputing
    # their embeddings
    with open(settings.PATH_TO_EMBEDDING_DICT, 'wb') as stream:
        pickle.dump(path_to_embed_dict, stream)
        print(f"Done creating path-to-embed-dict at {settings.PATH_TO_EMBEDDING_DICT}")


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
        emoclassifier = cf.EmotionClassifier(
                    lecture_instance=lecture_instance, 
                    target_emotions=settings.TARGET_EMOTIONS
                    )
        direct_euclid_classifier = cf.DirectEuclid(
                    pickle_path=settings.ENCODING_LIST, 
                    confidence_threshold=settings.CONFIDENCE
                    )
        knn_classifier = cf.KNN(
                    pickle_path=settings.KNN_EMBEDDING_MAP,
                    confidence_threshold=settings.CONFIDENCE
                    )
        svm_classifier = cf.SVM(
                    pickle_path=settings.SVM_EMBEDDING_MAP,
                    confidence_threshold=settings.CONFIDENCE
        )
        lecture_processing_time_start = time.time()
        frame_index = 0

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
            
            # Predict emotions
            for i in range(no):
                print(f"Predicting emotions for Face [{i+1}]")
                (top, right, bottom, left) = boxes[i]
                face = frame[top:top+right, bottom:bottom+left]
                if len(list(face)) > 0:
                    emoclassifier.predict_emotions(image=frame, threshold=settings.ADJACENT_THRESHOLD)

            # Get the embeddings of every face in the image
            embedding_list = [x for x in face_recognition.face_encodings(frame, known_face_locations=boxes)]
            # prediction output is a list of id 
            if settings.PREDICTION_MODE == "svm":
                # Prediction using svm
                recognized = svm_classifier.predict(face_encodings=embedding_list)
            elif settings.PREDICTION_MODE == "knn":
                # Prediction using knn
                recognized = knn_classifier.predict(
                                face_encodings=embedding_list, 
                                face_locations=boxes
                                )
            elif settings.PREDICTION_MODE == "direct-euclid":
                # Predict using direct euclid comparison
                recognized = direct_euclid_classifier.predict(face_encodings=embedding_list)
            # discard unknown in set if it exists
            if recognized:
                _id.update(recognized)
                _id.discard("unknown")
            for i in _id:
                if int(i) in registered_student_ids and not lecture_instance.lock:
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
        stop_lecture_time = time.time()
        print(f"Lecture {lecture_instance.course.name}-{lecture_instance.id} was stopped, exiting attendance, {frame_index} frame(s) processed")
        print(f"Lecture {lecture_instance.course.name}-{lecture_instance.id} attendance taking process ran for {round(stop_lecture_time - lecture_processing_time_start, 1)} seconds")
        print("##############################################################################")

