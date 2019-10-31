import numpy as np
import os
import hashlib
# import matplotlib.pyplot as plt
# import cv2
# from sklearn.decomposition import PCA
# from mpl_toolkits.mplot3d import Axes3D
# from mpl_toolkits.mplot3d import proj3d
# from imageio import imread
# from skimage.transform import resize
# from scipy.spatial import distance
# from keras.models import load_model


# def generate_pca_plot(image_embeddings, image_path):
#     """
#     Generate pca plot from a dictionary of lists
#     """
#     if not isinstance(image_embeddings, list):
#         raise ValueError("Image embeddings must be a dictionary of lists")
#     X = list()
#     for embedding in image_embeddings.values():
#         X.append(embedding)
#     fig = plt.figure(figsize=(8,8))
#     ax = fig.add_subplot(111, projection='3d')
#     pca = PCA(n_components=len(image_embeddings)).fit(X)
#     # transform the PCA
#     for key, val in image_embeddings:
#         transform = pca.transform(val)
#         ax.plot(*transform, alpha=0.5, label=key)
#     plt.title("Embedding vector")
#     ax.legend(loc='upper-right')
#     plt.savefig(image_path)
        

def get_id_from_enc(encoding_list_tuple, encoding):
    """
    Get corresponding id from the encoding list of tuples

    encoding_list_tuple contains tuples of encodings and their corresponding id's
    encoding is the encoding to compare against
    """
    for i in encoding_list_tuple:
        if i[0] == list(encoding):
            return i[1]
    return None

def get_encodings(encoding_list):
    """
    Get all encoding from the list of tuples
    """
    encoding = [i[0] for i in encoding_list]
    return encoding

def get_hash(imagebytes):
    """
    Generate image hash for a value
    """
    hashobj = hashlib.md5(imagebytes)
    return hashobj.hexdigest()