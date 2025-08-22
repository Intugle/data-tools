import logging
import os

from intugle.core import settings

log = logging.getLogger(__name__)


def di_initalizer():
    MAX_RETRIES = 5
    par_vec_path = os.path.join(
    settings.MODEL_DIR_PATH, "dependant", "datatype_l1_identification"
)

    import nltk

    from .paragraph_vectors import (
        initialise_nltk,
    )

    nltk_local_path = os.path.join(par_vec_path, "nltk_data")
    nltk.data.path.append(nltk_local_path)

    count = MAX_RETRIES
    while count > 0:
        try:
            initialise_nltk()
            return
        except Exception as ex:
            log.error(
                f"[!] Error initating nltk , word embeddings and pretrained doc 2 vec model : {ex} ... \n\n Retries left {count}"
            )
            count -= 1