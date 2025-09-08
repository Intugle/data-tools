import logging
import os

from datetime import datetime

import joblib
import numpy as np
import pandas as pd

from intugle.core.settings import settings

log = logging.getLogger(__name__)


class L1Model:
    
    model_objects_directory = os.path.join(settings.MODEL_DIR_PATH, "model_objects", "datatype_l1_identification")
    model_results_directory = os.path.join(settings.MODEL_RESULTS_PATH, 'datatype_l1_identification')

    def __init__(self, *args, **kwargs):
        if not os.path.exists(self.model_objects_directory):
            raise FileNotFoundError(f"No models at {self.model_objects_directory}")
        
    # ====================================================================
    # group_labels: 
    #  - groups the similar datatypes into one single type
    # Parameters: 
    #     datatype- input datatype 
    # ====================================================================     
    def __group_labels(self, datatype: str) -> str:
        
        # groups the similar datatypes into one single type
        if datatype in ['Short_Integer', 'Long_Integer']:
            return 'Integer'
        elif datatype in ['Short_Float', 'Long_Float']:
            return 'Float'
        elif datatype in ['Short_Alphanumeric', 'Long_Alphanumeric']:
            return 'Alphanumeric'
        elif datatype in ['Open_ended_long_text', 'Open_ended_short_text']:
            return 'Open_ended_text'
        elif datatype == 'Close_ended_short_text':
            return 'Close_ended_text'
        else:
            return datatype
        
    # ====================================================================
    # feature_subset: 
    #  - Returns the list of required features for the modeling
    # ====================================================================             
    def feature_subset(self) -> list:
        
        log.info('Subsetting the char, par, word, rest features')
        feats_cols = ['dateRatio', 'wordlen_mean', 'rangeRatio', 'floatRatio', 'zero_flag', 'intRatio',
                      'alphaNumRatio', 'alphaRatio', 'frac_unique_sample', 'flag_numcells']
        
        # Returns the list of required features for the modeling
        return feats_cols
     
    # ====================================================================
    # model_prediction: 
    #  - Features subset from the dataset for prediction 
    #  - Loading the model objects and encoder objects for model prediction
    #  - Model prediction on the test dataset and inverse transform to get the labels for the encoder
    #  - Subset the required columns based on the process type and return the predicted dataframe
    # Parameters: 
    #    test_df - test dataframe with features for model prediction
    #    model_version - model version
    #    process_type - train/inference for getting the prediction    
    # ====================================================================                      
    def model_prediction(self, test_df: pd.DataFrame, model_version=datetime.now().strftime('%d%m%Y'),
                         process_type: str = 'train') -> pd.DataFrame:
                
        X_test = test_df.copy()
        
        del test_df
        
        # Features subset from the dataset for prediction          
        features_list = self.feature_subset()
            
        # Loading the model objects for model prediction
        # logger.debug('Reading the model objects')

# 
        model_path = os.path.join(self.model_objects_directory, 'di_l1_classifier_xgb_' + model_version + '.pkl')
        encoder_path = os.path.join(self.model_objects_directory, 'di_l1_classifier_encoder_' + model_version + '.pkl')
        with open(model_path, 'rb') as f:
            clf_model = joblib.load(f) 
        log.info("[*] Loaded L1 classifier model")
        # Loading the encoder objects for model prediction
        with open(encoder_path, 'rb') as f:
            encoder = joblib.load(f)
        log.info("[*] Loaded L1 Encoder")
        
        # Model prediction on the test dataset and inverse transform to get the labels for the encoder
        log.info('[*] Started the model prediction')
        
        predicted_model_prob = clf_model.predict_proba(X_test[features_list].values)
        predicted_prob_class = [(pred[np.argmax(pred)], np.argmax(pred)) for pred in predicted_model_prob]
        predicted_prob = [val[0] for val in predicted_prob_class]        
        predicted_label = [encoder.inverse_transform([val[1]])[0] for val in predicted_prob_class]
        
        log.info('[*] Completed the model prediction on test data')
        
        # Storing the model results in predicted results
        log.info('[*] Storing the model prediction results')

        X_test['predicted_datatype_l1'] = predicted_label
        X_test['predicted_probability_l1'] = predicted_prob
             
        # Subset the required columns based on the process type
        
        return X_test[['table_name', 'column_name', 'predicted_datatype_l1', 'predicted_probability_l1']]
    