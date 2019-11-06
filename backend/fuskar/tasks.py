from __future__ import absolute_import
import os
import cv2
import time
import pickle
import numpy as np
from huey import crontab
from django.conf import settings
from django.db.utils import OperationalError
from EmoPy.src.fermodel import FERModel
from huey.contrib.djhuey import periodic_task, task, lock_task, enqueue
from fuskar.models import Lecture, Student, Emotion
from fuskar.utils.camera import get_frame
from fuskar.utils.helpers import get_id_from_enc, get_encodings, generate_pca_plot
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

def predict_emotions(model, image, lecture_instance):
    """
    Predict the emotions and add to lecture object
    """
    # get difference of the highest member of the list
    maxdiff = lambda lst: [(max(lst) - lst[i])<=settings.ADJACENT_THRESHOLD for i in range(0,len(lst)-1)]
    gray_image = image
    if len(image.shape) > 2:
        gray_image = cv2.cvtColor(image, code=cv2.COLOR_BGR2GRAY)
    resized_image = cv2.resize(gray_image, model.target_dimensions, interpolation=cv2.INTER_LINEAR)
    final_image = np.array([np.array([resized_image]).reshape(list(model.target_dimensions)+[model.channels])])
    prediction = model.model.predict(final_image)
    # normalized_prediction = [x/sum(prediction) for x in prediction]
    prediction = list(prediction[0])
    print(prediction)
    emotions = list()
    a = maxdiff(prediction)
    for index, val in enumerate(a):
        if val:
            emotions.append(settings.TARGET_EMOTIONS[index])

    print(f"Emotion(s) ==> {emotions}")
    if not lecture_instance.lock:
        for emotion_detected in emotions:
            emotion = Emotion.objects.create(emotion=emotion_detected)
            lecture_instance.emotions.add(emotion)

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
        # Create and train the SVC classifier
        clf = svm.SVC(gamma='scale', probability=True)
        clf.fit(encodings, id_)
        with open(settings.SVM_EMBEDDING_MAP, 'wb') as output:
            print("Creating embedding map")
            pickle.dump(clf, output)
            print(f"Done creating embedding map at {settings.SVM_EMBEDDING_MAP}")
        with open(settings.PATH_TO_EMBEDDING_DICT, 'wb') as stream:
            pickle.dump(path_to_embed_dict, stream)
            print(f"Done creating path-to-embed-dict at {settings.PATH_TO_EMBEDDING_DICT}")
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
    global stopped
    if not Lecture.objects.get(id=lecture_instance_id).lock:
        print("##############################################################################")
        lecture_instance = Lecture.objects.get(id=lecture_instance_id)
        model = FERModel(settings.TARGET_EMOTIONS, verbose=False)
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
            
            # Predict emotions
            for i in range(no):
                print(f"Predicting emotions for Face [{i+1}]")
                box = boxes[i]
                y_start = box[1]
                y_end = y_start + box[3]
                x_start = box[0]
                x_end = x_start + box[2]
                predict_emotions(model, frame[y_start:y_end, x_start:x_end], lecture_instance)

            # Get the embeddings of every face in the image
            embedding_list = [x for x in face_recognition.face_encodings(frame, known_face_locations=boxes)]
            # prediction output is a list of id 
            if settings.USE_EMBEDDING:
                # Prediction using SVM_EMBEDDING_MODE
                # Predict all the faces in the test image using the trained classifier
                prediction_set = set({})
                if len(embedding_list) > 0:
                    probability = list(clf.predict_proba(embedding_list))
                    print(probability)
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
                        # TODO: create a voting system like KNN to increase performance
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
            time.sleep(2)
        stopped = True
        stop_lecture_time = time.time()
        print(f"Lecture {lecture_instance.course.name}-{lecture_instance.id} was stopped, exiting attendance, {frame_index} frame(s) processed")
        print(f"Lecture {lecture_instance.course.name}-{lecture_instance.id} attendance taking process ran for {round(stop_lecture_time - lecture_processing_time_start, 1)} seconds")
        print("##############################################################################")

