import os
import pickle
from django.db import models
from django.conf import settings
from django.dispatch import receiver
from fuskar.models import Image, Lecture, Course
from fuskar.utils.camera import video_stream
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
embedding_map = os.path.join(cache_path, 'cache', 'embedding-map.pkl')

@receiver(models.signals.post_delete, sender=Image)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    """
    Deletes file from filesystem
    when corresponding `Image` object is deleted.
    """
    if instance.file:
        if os.path.isfile(instance.file.path):
            os.remove(instance.file.path)

@receiver(models.signals.post_create, sender=Image)
def retrain_embedding_on_create(sender, instance, **kwargs):
    """
    Retrains the scikit-learn embedding map
    When a new Image is created
    """
    global media_path, cache_path, 

    encodings = []
    id_ = []

    
    # Training directory
    image_dir = os.path.join(media_path, 'images')
    train_dir = os.listdir(image_dir)

    # Loop through each folder in the image directory
    for person in train_dir:
        person_folder = os.path.join(image_dir, person)
        person_folder_listing = os.listdir(person_folder)

        # Loop through each training image for the current person
        for image in person_folder_listing:
            # Get the face encodings for the face in each image file
            image_path = os.path.join(person_folder, image)
            face = face_recognition.load_image_file(image_path)
            face_bounding_boxes = face_recognition.face_locations(face)

            #If training image contains none or more than faces, print an error message and exit
            if len(face_bounding_boxes) != 1:
                print(person + "/" + image + " contains none or more than one faces and can't be used for training.")
                exit()
            else:
                face_enc = face_recognition.face_encodings(face)[0]
                # Add face encoding for current image with corresponding label (name) to the training data
                encodings.append(face_enc)
                id_.append(person)
    
    # Create and train the SVC classifier
    clf = svm.SVC(gamma='scale')
    clf.fit(encodings,id_)
    pickle.dump(clf, embedding_map)

# TODO: create a receiver to start the attendance taking process on creation of lecture object
@receiver(models.signals.post_create, sender=Lecture)
def take_attendance_on_lecture_create(sender, instance, **kwargs):
    """
    Begins taking attendance
    Once a Lecture object is created
    """
    global embedding_map
    
    # retrieve classifier from the pickled embedding map
    if os.path.isfile(embedding_map):
        clf = pickle.load(embedding_map)
    else:
        print("Embedding Map cannot be found, exiting")
        exit()

    # retrieve students registered for this course
    course = instance.course
    students = course.registered_students
    print("Retrieving student ID")
    registered_student_ids = [int(_id) for _id in students.id]
    # video_stream is yielding all the images one by one
    frames = video_stream(stream=False)
    for i in frames:
        # Find all the faces in the test image using the default HOG-based model
        face_locations = face_recognition.face_locations(i)
        no = len(face_locations)
        print("Number of faces detected: ", no)

        # Predict all the faces in the test image using the trained classifier
        for i in range(no):
            test_image_enc = face_recognition.face_encodings(test_image)[i]
            _id = clf.predict([test_image_enc])
            print(_id)
            if int(_id) in registered_student_ids:
                instance.add(int(_id))
            else:
                print("Student was not registered for the course")
