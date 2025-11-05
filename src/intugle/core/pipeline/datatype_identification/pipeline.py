import logging

import pandas as pd

from intugle.core.settings import settings

from .feature_creation import DIFeatureCreation
from .initialize import di_initalizer
from .l1_model import L1Model

log = logging.getLogger(__name__)


MODEL_VERSION = settings.DI_MODEL_VERSION


class DataTypeIdentificationPipeline:

    # NUM_SAMPLES = DI_CONFIG["L2PARAMS"]["SAMPLE_SIZE"]

    VALID_INVALID_MAPPING = {
        "integer": ["intRatio"],
        "others": [],
        "float": ["floatRatio"],
        "range_type": ["rangeRatio"],
        "date & time": ["dateRatio"],
        "close_ended_text": ["alphaRatio", "numericRatio", "alphaNumRatio"],
        "open_ended_text": ["alphaRatio", "numericRatio", "alphaNumRatio"],
        "alphanumeric": ["alphaNumRatio", "alphaRatio", "numericRatio"],
    }

    def __init__(self, l1_model: L1Model = None, feature_creator: DIFeatureCreation = None, *args, **kwargs):
        
        di_initalizer()

        self.__feature_creator = DIFeatureCreation() if feature_creator is None else feature_creator
        
        self.__l1_model = L1Model() if l1_model is None else l1_model

    def create_feature(self, assets: list[dict],) -> pd.DataFrame:
        """
        Run DI Feature creation process for a dataset
        Parameters
        ----------
        source_path (os.path): full folder path to the dataset.
        parallel (bool): flag for whether to run parallel processing on feature creation or not.
        batched (bool): flag to whether run features creation on batches of columns.

        Returns
        -------
        pd.DataFrame: DI features as a pandas dataframe where each row is a feature of a specific column , of a specific table.
        """
        return self.__feature_creator(assets=assets,)

    def l1_model_run(self, features: pd.DataFrame, *args, **kwargs) -> pd.DataFrame:
        """
        Runs DI L1 model to identify datatypes

        Parameters
        ----------
        features (pd.DataFrame): DI specific features obtained from create_feature()
        model_version (str): version of model to run L1 Classifier for.

        Returns
        -------
        pd.DataFrame: predicted datatypes L1 as a dataframe
        """
        return self.__l1_model.model_prediction(features, model_version=kwargs.get("model_version", MODEL_VERSION),)
    
    def __call__(self, sample_values_df: pd.DataFrame, *args, **kwargs):

        feature = self.__feature_creator(sample_values_df=sample_values_df)
        
        log.info("[*] Running L1 Model")
        
        l1_pred_result = self.l1_model_run(feature, model_version=settings.DI_MODEL_VERSION, *args, **kwargs)

        log.info("[*] Merging L1 result and L1 features")
        
        l1_pred_result = pd.merge(l1_pred_result, feature, on=['table_name', 'column_name'])
        
        del feature
 
        return l1_pred_result
    