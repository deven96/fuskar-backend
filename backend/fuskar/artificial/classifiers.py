"""
Implements all the classifiers to be used by Fuskar
"""
import os
import math
import cv2
import pickle
import numpy as np
import face_recognition
from sklearn import neighbors, svm
from EmoPy.src.fermodel import FERModel
from fuskar.models import Emotion
from fuskar.utils.helpers import get_id_from_enc, get_encodings


class EmotionClassifier(object):
    """
    Predicts emotions based on the stored Emotions 
    for a particular lecture instance
    """
    def __init__(self, lecture_instance, target_emotions):
        self.lecture_instance = lecture_instance
        self.target_emotions = target_emotions
        self.model = FERModel(target_emotions, verbose=False)

    def add_to_db(self, emotions):
        """
        Add emotions to lecture instance

        :param emotions: emotions to be added to lecture_instance
        :type emotions: list
        """
        print(f"Emotion(s) ==> {emotions}")
        if not self.lecture_instance.lock:
            for emotion_detected in emotions:
                emotion = Emotion.objects.create(emotion=emotion_detected)
                self.lecture_instance.emotions.add(emotion)
        

    def predict_emotions(self, image, threshold, add_to_db=True):
        """
        Predict emotions in a certain image
        and add to the lecture instance

        :param image: loaded image matrix either using cv2 or PIL
        :type image: np.array
        """
        maxdiff = lambda lst: [(max(lst) - lst[i])<=threshold and lst[i] !=0 for i in range(0,len(lst)-1)]
        gray_image = image
        if len(image.shape) > 2:
            gray_image = cv2.cvtColor(image, code=cv2.COLOR_BGR2GRAY)
        resized_image = cv2.resize(gray_image, self.model.target_dimensions, interpolation=cv2.INTER_LINEAR)
        final_image = np.array([np.array([resized_image]).reshape(list(self.model.target_dimensions)+[self.model.channels])])
        prediction = self.model.model.predict(final_image)
        # normalized_prediction = [x/sum(prediction) for x in prediction]
        prediction = list(prediction[0])
        print(prediction)
        emotions = list()
        a = maxdiff(prediction)
        for index, val in enumerate(a):
            if val:
                emotions.append(self.target_emotions[index])
        if add_to_db:
            self.add_to_db(emotions)
        return emotions

class KNN:
    """
    Implements a K-Nearest-Neighbour classification system for 
    Prediction
    """

    name = "knn"

    def __init__(self, pickle_path, confidence_threshold):
        """
        set pickle path and confidence threshold

        :param confidence_threshold: confidence threshold for face classification. the smaller it is, the more chance
            of mis-classifying an unknown person as a known one.
        """
        self.pickle_path = pickle_path
        self.confidence_threshold = confidence_threshold

    @staticmethod
    def train(X, Y, pickle_path, n_neighbors=None, knn_algo='ball_tree', verbose=True):
        """
        Train the KNN machine
        """
        # Automatically determine how many neighbors to use for weighting in the KNN classifier
        if not n_neighbors:
            n_neighbors = int(round(math.sqrt(len(X))))
            if verbose:
                print(f"Chose n_neighbors automatically: {n_neighbors}")

        # Create and train the KNN classifier
        knn_clf = neighbors.KNeighborsClassifier(n_neighbors=n_neighbors, algorithm=knn_algo, weights='distance')
        knn_clf.fit(X, Y)

        # Save the trained KNN classifier
        if pickle_path:
            if not os.path.exists(os.path.dirname(pickle_path)):
                os.mkdir(os.path.dirname(pickle_path))
            with open(pickle_path, 'wb') as f:
                pickle.dump(knn_clf, f)
                if verbose:
                    print(f"Saved pickled KNN to path {pickle_path}")

        return knn_clf

    def predict(self, face_encodings, face_locations, knn_clf=None):
        """
        Recognizes faces in given image using the trained KNN classifier

        :param face_encodings: encodings from image
        :param face_locations: locations of faces
        :param knn_clf: (optional) a knn classifier object. if not specified, model_save_path must be specified.
        :return: a list of id and face locations for the recognized faces in the image: [(id, bounding box), ...].
            For faces of unrecognized persons, the name 'unknown' will be returned.
        """
        print(f"Predicting using {self.name} mode")
        distance_threshold = 1 - self.confidence_threshold
        if knn_clf is None and self.pickle_path is None:
            raise Exception("Must supply knn classifier either thourgh knn_clf or pickle_path")

        if not knn_clf:
            with open(self.pickle_path, 'rb') as stream:
                knn_clf = pickle.load(stream)
        
        if len(face_encodings) > 0:
            closest_distances = knn_clf.kneighbors(face_encodings, n_neighbors=1)
            are_matches = [closest_distances[0][i][0] <= distance_threshold for i in range(len(face_locations))]

            # Predict classes and remove classifications that aren't within the threshold
            return [pred if rec else "unknown" for pred, _, rec in zip(knn_clf.predict(face_encodings), face_locations, are_matches)]

        

class DirectEuclid:
    """
    Runs a direct euclidean distance comparsion against every other embedding
    """

    name = "direct-euclid"

    def __init__(self, pickle_path, confidence_threshold):
        """
        set pickle path and confidence threshold
        """
        self.pickle_path = pickle_path
        self.confidence_threshold = confidence_threshold

    @staticmethod
    def train(pickle_path, encoding_list_tuple, verbose=True):
        """
        Doesn't actually train, just saves the path to pickle path
        """
        with open(pickle_path, 'wb') as output:
            pickle.dump(encoding_list_tuple, output)
            print(f"Saved encoding list to {pickle_path}")


    def predict(self, face_encodings):
        """
        Use the pickled classifier to predict
        """
        print(f"Predicting using {self.name} mode")
        predictions = list()
        distance_threshold = 1 - self.confidence_threshold
        with open(self.pickle_path, 'rb') as stream:
                encoding_list_tuple = pickle.load(stream)

        encoding_list = get_encodings(encoding_list_tuple)
        if len(face_encodings) > 0:
            for i in face_encodings:
                results = face_recognition.face_distance(encoding_list, i)
                # get min face distance and compare
                min_distance = min(results)
                index = list(results).index(min_distance)
                if index:
                    encoding = encoding_list[index]
                    single_id = get_id_from_enc(encoding_list_tuple, encoding)
                    if min_distance <= distance_threshold:
                        predictions.append(single_id)
                    else:
                        predictions.append("unknown")
            return predictions



class SVM:
    """
    SVM classifier
    """

    name = "svm"

    def __init__(self, pickle_path, confidence_threshold):
        """
        set pickle path and confidence threshold

        :param confidence_threshold: confidence threshold for face classification. the smaller it is, the more chance
            of mis-classifying an unknown person as a known one.
        """
        self.pickle_path = pickle_path
        self.confidence_threshold = confidence_threshold

    @staticmethod
    def train(X, Y, pickle_path, probability=True, gamma="scale", verbose=True):
        """
        Train the SVM machine
        """

        # Create and train the SVM classifier
        clf = svm.SVC(gamma=gamma, probability=probability)
        clf.fit(X, Y)

        # Save the trained KNN classifier
        if pickle_path:
            if not os.path.exists(os.path.dirname(pickle_path)):
                os.mkdir(os.path.dirname(pickle_path))
            with open(pickle_path, 'wb') as f:
                pickle.dump(clf, f)
                if verbose:
                    print(f"Saved pickled SVM to path {pickle_path}")
        return clf

    def predict(self, face_encodings, svm_clf=None):
        """
        Recognizes faces in given image using the trained KNN classifier

        :param face_encodings: encodings from image
        :param svm_clf: (optional) an svm classifier object. if not specified, model_save_path must be specified.
        :return: a list of id for the recognized faces in the image: [1, 2, ...]
            For faces of unrecognized persons, the name 'unknown' will be returned.
        """
        print(f"Predicting using {self.name} mode")
        prediction_set = list()

        if svm_clf is None and self.pickle_path is None:
            raise Exception("Must supply svm classifier either thourgh svm_clf or pickle_path")

        if not svm_clf:
            with open(self.pickle_path, 'rb') as stream:
                svm_clf = pickle.load(stream)
            classes = svm_clf.classes_
        
        if len(face_encodings) > 0:
            probability = list(svm_clf.predict_proba(face_encodings))
            for i in probability:
                highest_probability =  max(i)
                if highest_probability >= self.confidence_threshold:
                    index = list(i).index(highest_probability)
                    prediction = classes[index]
                    prediction_set.append(prediction)
                else:
                    prediction_set.append("unknown")
        return prediction_set