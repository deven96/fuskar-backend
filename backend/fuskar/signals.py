import os
import pickle
from django.db import models
from django.conf import settings
from django.dispatch import receiver
from fuskar.models import Image, Lecture, Course
from fuskar.utils.camera import get_frame
from fuskar.utils.helpers import get_id_from_enc, get_encodings ,get_true_index
import face_recognition
from sklearn import svm

# global variables
if settings.DEBUG:
    media_path = settings.MEDIA_ROOT
    cache_path = settings.CACHE_ROOT
else:
    media_path = settings.MEDIA_URL
    cache_path = settings.CACHE_URL
# save the embedding map in the cache directory
svm_embedding_map = os.path.join(cache_path, 'cache', 'embedding-map.pkl')
encoding_map = os.path.join(cache_path, 'cache', 'encoding-list.pkl')

@receiver(models.signals.post_delete, sender=Image)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    """
    Deletes file from filesystem
    when corresponding `Image` object is deleted.
    """
    print("Image object signal-delete received, deleting hardcopy")
    if instance.file:
        if os.path.isfile(instance.file.path):
            os.remove(instance.file.path)


@receiver(models.signals.post_save, sender=Image)
def retrain_embedding_on_image_save(sender, instance, **kwargs):
    """
    Retrains the scikit-learn embedding map
    When a new Image is created
    """
    global media_path, cache_path, svm_embedding_map, encoding_map

    encodings = []
    id_ = []

    
    # Training directory
    image_dir = os.path.join(media_path, 'images')
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
        with open(svm_embedding_map, 'wb') as output:
            print("Creating embedding map")
            pickle.dump(clf, output)
    else:
        print("Cannot create SVM with one class, switching to encoding mode")
        settings.USE_EMBEDDING = False
    with open(encoding_map, 'wb') as output:
        print("Creating encoding map")
        pickle.dump(encoding_list_tuple, output)


# @receiver(models.signals.post_save, sender=Lecture)
# def take_attendance_on_lecture_create(sender, instance, **kwargs):
#     """
#     Begins taking attendance
#     Once a Lecture object is created
#     """
#     global svm_embedding_map, encoding_map
    
#     # retrieve classifier from the pickled embedding map
#     if os.path.isfile(svm_embedding_map):
#         with open(svm_embedding_map, 'rb') as stream:
#           clf = pickle.load(stream)
#     else:
#         print("Embedding Map cannot be found, Switching to face_distance mode")
#     if not settings.USE_EMBEDDING:
#         with open(encoding_map, 'rb') as stream:
#             encoding_list_tuple = pickle.load(stream)

#     # retrieve students registered for this course
#     course = instance.course
#     students = course.registered_students
#     print("Retrieving student ID")
#     registered_student_ids = [int(_id) for _id in students.id]
#     # video_stream is yielding all the images one by one
#     frames = video_stream(stream=False)
#     _id = set({})
#     for i in frames:
#         # Find all the faces in the test image using the default HOG-based model
#         face_locations = face_recognition.face_locations(i)
#         no = len(face_locations)
#         print("Number of faces detected: ", no)

#         # Get the embeddings of every face in the image
#         embedding_list = [x for x in face_recognition.face_encodings(i)]
#         # prediction output is a list of id 
#         if settings.USE_EMBEDDING:
#             # Prediction using SVM_EMBEDDING_MODE
#             # Predict all the faces in the test image using the trained classifier
#             prediction_set = set({clf.predict(embedding_list)})
#             _id.union(prediction_set)
#         else:
#             # Prediction using ENCODING_MODE
#             encoding_list = get_encodings(encoding_list_tuple)
#             for i in embedding_list:
#                 results = face_recognition.compare_faces(encoding_list, i)
#                 index = get_true_index(results)
#                 if index:
#                     encoding = encoding_list[index]
#                     single_id = get_id_from_enc(encoding_list_tuple, encoding)
#                     _id.add(single_id)

#         # in every frame, take all the id's predicted and create a many to many instance 
#         # on the lecture object
#         for i in _id:
#             if int(i) in registered_student_ids:
#                 instance.add(int(i))
#             else:
#                 print("Student {} was recognized but was not registered for the course". format(i))

def test_attendance():
    """
    Begins taking attendance
    Once a Lecture object is created
    """
    global svm_embedding_map, encoding_map
    
    # retrieve classifier from the pickled embedding map
    if os.path.isfile(svm_embedding_map):
        with open(svm_embedding_map, 'rb') as stream:
            print("Loading Embedding Map for SVM-EMBEDDING mode")
            clf = pickle.load(stream)
    else:
        print("Embedding Map cannot be found, Switching to FACE-ENCODING mode")
        settings.USE_EMBEDDING = False
    if not settings.USE_EMBEDDING:
        with open(encoding_map, 'rb') as stream:
            print("Loading Encoding list for FACE-ENCODING mode")
            encoding_list_tuple = pickle.load(stream)

    # video_stream is yielding all the images one by one
    frames = get_frame()
    _id = set({})
    for frame in frames:
        print("Frame obtained from stream", frame)
        # Find all the faces in the test image using the default HOG-based model
        face_locations = face_recognition.face_locations(frame, model="cnn")
        no = len(face_locations)
        print("Number of faces detected: ", no)

        # Get the embeddings of every face in the image
        embedding_list = [x for x in face_recognition.face_encodings(frame)]
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
        print("Outside use embeddings")

        print("ID's detected",_id)