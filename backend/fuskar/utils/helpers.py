import numpy as np
import os
import matplotlib.pyplot as plt
import cv2
from sklearn.decomposition import PCA
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d import proj3d
from imageio import imread
from skimage.transform import resize
from scipy.spatial import distance
from keras.models import load_model



def prewhiten(x):
    """
    Pre-whitening step for processing an image
    """
    if x.ndim == 4:
        axis = (1, 2, 3)
        size = x[0].size
    elif x.ndim == 3:
        axis = (0, 1, 2)
        size = x.size
    else:
        raise ValueError('Dimension should be 3 or 4')

    mean = np.mean(x, axis=axis, keepdims=True)
    std = np.std(x, axis=axis, keepdims=True)
    std_adj = np.maximum(std, 1.0/np.sqrt(size))
    y = (x - mean) / std_adj
    return y

def l2_normalize(x, axis=-1, epsilon=1e-10):
    """
    Calculate L2 normalization for the array
    """
    output = x / np.sqrt(np.maximum(np.sum(np.square(x), axis=axis, keepdims=True), epsilon))
    return output

def load_and_align_images(filepaths=None, image_arrays=None, margin=10, image_size=160):
    """
    Load images and align them
    """
    cascade = cv2.CascadeClassifier(cascade_path)
    
    aligned_images = []
    if filepaths:
        for filepath in filepaths:
            img = imread(filepath)

            faces = cascade.detectMultiScale(img,
                                            scaleFactor=1.1,
                                            minNeighbors=3)
            (x, y, w, h) = faces[0]
            cropped = img[y-margin//2:y+h+margin//2,
                        x-margin//2:x+w+margin//2, :]
            aligned = resize(cropped, (image_size, image_size), mode='reflect')
    elif image_arrays:
        for arr in image_arrays:
            faces = cascade.detectMultiScale(arr,
                                            scaleFactor=1.1,
                                            minNeighbors=3)
            (x, y, w, h) = faces[0]
            cropped = img[y-margin//2:y+h+margin//2,
                        x-margin//2:x+w+margin//2, :]
            aligned = resize(cropped, (image_size, image_size), mode='reflect')
    
    aligned_images.append(aligned)        
    return np.array(aligned_images)

def calc_embs(filepaths, image_arrays, model, margin=10, batch_size=1):
    """
    Calculate embeddings of multiple images or filepaths
    """
    if filepaths:
        aligned_images = prewhiten(load_and_align_images(filepaths=filepaths, margin=margin))
    elif image_arrays:
        aligned_images = prewhiten(load_and_align_images(image_arrays=image_arrays, margin=margin))
    pd = []
    for start in range(0, len(aligned_images), batch_size):
        pd.append(model.predict_on_batch(aligned_images[start:start+batch_size]))
    embs = l2_normalize(np.concatenate(pd))

    return embs

def calc_dist(reference_embedding, comparison_embedding):
    """
    Euclidean distance of embeddings
    """
    if isinstance(comparison_embedding, list):
        distance_score = [distance.euclidean(reference_embedding, i) for i in comparison_embedding]
    else:
        distance_score = distance.euclidean(reference_embedding, comparison_embedding)
    return distance_score


def calc_dist_plot(reference_embedding, comparison_embedding):
    """
    Calculate distance plot given two images
    """
    plt.subplot(1, 2, 1)
    plt.imshow(reference_embedding)
    plt.subplot(1, 2, 2)
    plt.imshow(comparison_embedding)
    plt.title("Distance is {}".format(calc_dist(reference_embedding, comparison_embedding)))

def generate_pca_plot(image_embeddings, image_path):
    """
    Generate pca plot from a dictionary of lists
    """
    if not isinstance(image_embeddings, list):
        raise ValueError("Image embeddings must be a dictionary of lists")
    X = list()
    for embedding in image_embeddings.values():
        X.append(embedding)
    fig = plt.figure(figsize=(8,8))
    ax = fig.add_subplot(111, projection='3d')
    pca = PCA(n_components=len(image_embeddings)).fit(X)
    # transform the PCA
    for key, val in image_embeddings:
        transform = pca.transform(val)
        ax.plot(*transform, alpha=0.5, label=key)
    plt.title("Embedding vector")
    ax.legend(loc='upper-right')
    plt.savefig(image_path)
        

def get_id_from_enc(encoding_list_tuple, encoding):
    """
    Get corresponding id from the encoding list of tuples

    encoding_list_tuple contains tuples of encodings and their corresponding id's
    encoding is the encoding to compare against
    """
    for i in encoding_list_tuple:
        for enc, id_ in i:
            if enc == enc:
                return id_
    return None

def get_encodings(encoding_list):
    """
    Get all encoding from the list of tuples
    """
    encoding = [i[0] for i in encoding_list]
    return encoding

def get_true_index(truth_list):
    """
    Get the index of True from a list of True/false
    """
    try:
        return truth_list.index(True)
    except ValueError:
        return None

