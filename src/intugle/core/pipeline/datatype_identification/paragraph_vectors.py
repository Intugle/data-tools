# ====================================================================
#  Importing the required python packages
# ====================================================================
import logging
import os

from datetime import datetime

import nltk

from nltk.corpus import stopwords

from intugle.core.settings import settings

log = logging.getLogger(__name__)


Doc2Vec = None
TaggedDocument = None

# ====================================================================
# tokenise: To convert the multiple words data into separate words if crosses the word limit
# Parameters: 
#     values - List of values or data
# ====================================================================


def tokenise(values: list) -> list:
    joined = " ".join(s for s in values if len(s) >= settings.DI_CONFIG['THRESHOLD']['TOKENIZE_WORD_LIMIT'])

    # stopwords need apostrophe
    filtered = "".join(
        e for e in joined if e.isalnum() or e.isspace() or e == "'"
    ).lower()

    if STOPWORDS_ENGLISH is None:
        initialise_nltk()
        
    return [
        word
        for word in nltk.word_tokenize(filtered)
        if len(word) >= settings.DI_CONFIG['THRESHOLD']['TOKENIZE_WORD_LIMIT'] and word not in STOPWORDS_ENGLISH
    ]


# ====================================================================
# initialise_pretrained_model: 
#  - Loads the pretrained model from the model path provided in the parameters
# Parameters: 
#     dim - Vector/Embedding dimension size
#     path - destination path for the trained model
# ====================================================================
    

model: Doc2Vec = None


def initialise_pretrained_model(path, dim):
    global model
    if model is not None:
        return
    
    start = datetime.now()
    filename = f"{path}/par_vec_trained_{dim}.pkl"
    
    model = Doc2Vec.load(filename)
    model.delete_temporary_training_data(keep_doctags_vectors=True, keep_inference=True)
    log.info(f"Initialise Doc2Vec Model, {dim} dim, process took {datetime.now() - start} seconds. (filename = {filename})")

    
# ====================================================================
# initialise_nltk: 
#  - Loads the nltk related objects required for training
# ====================================================================

STOPWORDS_ENGLISH = None


def initialise_nltk():
    
    global STOPWORDS_ENGLISH
    if STOPWORDS_ENGLISH is not None:
        return 
    
    par_vec_path = os.path.join(settings.MODEL_DIR_PATH, "dependant", "datatype_l1_identification")
    nltk_local_path = os.path.join(par_vec_path, "nltk_data")
    nltk.data.path.append(nltk_local_path)
    
    start = datetime.now()
    try:
        nltk.data.find('corpora/words')
    except LookupError:    
        nltk.download('words')
        
    try:
        nltk.data.find("tokenizers/punkt")
    except LookupError:
        nltk.download("punkt")
        
    try:
        nltk.data.find("corpora/stopwords.zip")
    except LookupError:
        nltk.download("stopwords")

    STOPWORDS_ENGLISH = stopwords.words("english")

    log.info(f"Initialised NLTK, process took {datetime.now() - start} seconds.")

