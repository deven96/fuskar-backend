from __future__ import absolute_import
import os
import pickle
import time
# import fuskar.signals
from celery import shared_task
from celery.task import Task
from celery.utils.log import get_task_logger
from django.conf import settings
from fuskar.models import Lecture
from fuskar.utils.camera import get_frame, capture_from_camera
from fuskar.utils.helpers import get_id_from_enc, get_encodings, get_true_index
import face_recognition
from sklearn import svm

logger = get_task_logger(__name__)

@shared_task
def retrain_pkl():
    """
    Background task for retraining the pickled objects
    """
    encodings = []
    id_ = []

    
    # Training directory
    image_dir = os.path.join(settings.media_path, 'images')
    train_dir = os.listdir(image_dir)

    encoding_list_tuple = list()
    # Loop through each folder in the image directory
    for person in train_dir:
        person_folder = os.path.join(image_dir, person)
        person_folder_listing = os.listdir(person_folder)

        # Loop through each training image for the current person
        for image in person_folder_listing:
            # Get the face encodings for the face in each image file
            image_path = os.path.join(person_folder, image)
            face = face_recognition.load_image_file(image_path)
            try:
                face_enc = face_recognition.face_encodings(face)[0]
                # Add face encoding for current image with corresponding label (name) to the training data
                encodings.append(face_enc)
                id_.append(person)
                # create list of encodings tuples
                encoding_list_tuple.append((face_enc, id_))
            except IndexError:
                pass
    if len(train_dir) > 1:
        # Create and train the SVC classifier
        settings.USE_EMBEDDING = True
        clf = svm.SVC(gamma='scale')
        clf.fit(encodings, id_)
        with open(settings.SVM_EMBEDDING_MAP, 'wb') as output:
            logger.info("Creating embedding map")
            pickle.dump(clf, output)
    else:
        logger.info("Cannot create SVM with one class, switching to encoding mode")
        settings.USE_EMBEDDING = False
    with open(settings.ENCODING_MAP, 'wb') as output:
        logger.info("Creating encoding map")
        pickle.dump(encoding_list_tuple, output)
        logger.info("Done creating encoding map at {}".format(settings.ENCODING_MAP))


# TODO: install cuda support and cudacnn to enable using cuda for model=cnn
@shared_task
def test_attendance(lecture_instance_id):
    """
    Begins taking attendance
    Once a Lecture object is created
    """
    while not Lecture.objects.get(id=lecture_instance_id).stopped_at:
        lecture_instance = Lecture.objects.get(id=lecture_instance_id)
        logger.info(type(lecture_instance))
        course = lecture_instance.course
        students = course.registered_students.all()
        logger.info("Retrieving students ID")
        registered_student_ids = [int(student.id) for student in students]

        # retrieve classifier from the pickled embedding map
        if os.path.isfile(settings.SVM_EMBEDDING_MAP):
            with open(settings.SVM_EMBEDDING_MAP, 'rb') as stream:
                logger.info("Loading Embedding Map for SVM-EMBEDDING mode")
                clf = pickle.load(stream)
        else:
            logger.info("Embedding Map cannot be found, Switching to FACE-ENCODING mode")
            settings.USE_EMBEDDING = False
        if not settings.USE_EMBEDDING:
            with open(settings.ENCODING_MAP, 'rb') as stream:
                logger.info("Loading Encoding list for FACE-ENCODING mode")
                encoding_list_tuple = pickle.load(stream)

        # video_stream is yielding all the images one by one
        _id = set({})
        # while True:
        frame = get_frame()
        boxes = face_recognition.face_locations(frame)
        logger.info("Frame obtained from stream {}".format(frame))
        # Find all the faces in the test image using the default HOG-based model
        # face_locations = face_recognition.face_locations(frame, number_of_times_to_upsample=3)
        no = len(boxes)
        logger.info("Number of faces detected: {}".format(no))

        print(boxes)
        
        # Get the embeddings of every face in the image
        embedding_list = [x for x in face_recognition.face_encodings(frame, known_face_locations=boxes)]
        # prediction output is a list of id 
        if settings.USE_EMBEDDING:
            # Prediction using SVM_EMBEDDING_MODE
            # Predict all the faces in the test image using the trained classifier
            if len(embedding_list) > 0:
                prediction_set = set({clf.predict(embedding_list)})
                _id.union(prediction_set)
        else:
            # Prediction using ENCODING_MODE
            encoding_list = get_encodings(encoding_list_tuple)
            if len(embedding_list) > 0:
                for i in embedding_list:
                    results = face_recognition.compare_faces(encoding_list, i)
                    index = get_true_index(results)
                    if index:
                        encoding = encoding_list[index]
                        single_id = get_id_from_enc(encoding_list_tuple, encoding)
                        _id.add(single_id)
        for i in _id:
            if int(i) in registered_student_ids:
                lecture_instance.students_present.add(int(i))
            else:
                logger.info("Student {} was recognized but was not registered for the course". format(i))
        time.sleep(10)
