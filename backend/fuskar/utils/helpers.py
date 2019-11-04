import numpy as np
import os
import tkinter
import pickle
import matplotlib
import matplotlib.pyplot as plt
from fuskar.models import Student
from scipy.spatial import distance
from sklearn.decomposition import PCA
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d import proj3d
matplotlib.use('TkAgg')

def generate_pca_plot(save_fig_path, encoding_list_path):
    """
    Generate 3D PCA plot of the embeddings
    """
    X = list()
    with open(encoding_list_path, 'rb') as stream:
        encoding_list_tuple = pickle.load(stream)
    label_set = set({})
    for i in encoding_list_tuple:
        X.append(i[0])
        label_set.add(i[1])
    pca = PCA(n_components=3).fit(X)
    label_set_dict = dict()
    for i in label_set:
        label_set_dict[i] = []
    for i in encoding_list_tuple:
        label_set_dict[i[1]].append(i[0])
    
    label_set_transformed = dict()
    for i in label_set_dict:
        label_set_transformed[i] = pca.transform(label_set_dict[i])
    
    fig = plt.figure(figsize=(24,24))
    ax = fig.add_subplot(111, projection='3d')
    plt.rcParams['legend.fontsize'] = 10
    for i in label_set_transformed.keys():
        # plot the three axes
        student = Student.objects.get(id=int(i))
        ax.plot(label_set_transformed[i][:,0], label_set_transformed[i][:, 1], label_set_transformed[i][:, 2], 'o', markersize=8, alpha=0.5, label=student.full_name)
    
    plt.title("Embedding vector plot")
    ax.legend()
    ax.legend(loc='upper right')

    if not os.path.exists(save_fig_path):
        os.makedirs(os.path.dirname(save_fig_path))
    plt.savefig(save_fig_path)


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

def get_hash(image):
    """
    Generate image hash for a value
    """
    import hashlib
    
    hashobj = hashlib.md5(image.read()).hexdigest()
    print(hashobj)
    return hashobj
