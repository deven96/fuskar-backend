
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
