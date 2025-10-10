import os

from pathlib import Path

import yaml

ALIAS = {
    "DI": "datatype_identification",
    "LP": "link_prediction",
    "KI": "key_identification",
    "BG": "business_glossary",
    "DC": "domain_classification"
    }

ALLOWED_PIPELINE_NAME = ["KI", "LP", "BG", "DI", "DC"]

CODE_PATH = Path(os.path.split(os.path.abspath(__file__))[0]).parent


def load_model_configuration(pipeline_name: str, custom_config: dict):
    '''
        For loading each pipeline configuration
    '''

    assert pipeline_name in ALLOWED_PIPELINE_NAME, f"[!] pipeline name can be only {ALLOWED_PIPELINE_NAME} not {pipeline_name}"
    
    default_config = {}

    if pipeline_name not in ["DC"]:
        default_config_file = os.path.join(CODE_PATH, "pipeline", ALIAS[pipeline_name.upper()], "config.yaml")
        with open(default_config_file, "r") as d_config_file:
            default_config = yaml.safe_load(d_config_file)
            
    if pipeline_name in ["DC"]:
        default_config = {
            
            "INCLUDE_DTYPES": True
        }
    try:
        user_config = custom_config[pipeline_name.upper()] 
    except Exception:
        user_config = {}

    # update the default config if there was a custom configuration
            
    for key in user_config.keys():
        if key in default_config.keys(): 
            if isinstance(default_config[key], dict):
                if len(default_config[key]) <= 0:  # add new config if there was no config under a key 
                    default_config[key] = user_config[key]
                else:  # update the existing config dictionary
                    default_config[key].update(user_config[key])
            else:
                default_config[key] = user_config[key]
                
        else:  # if the corresponding config key not found then add a new config under that keys
            default_config[key] = user_config[key]
    
    return {**default_config}


def load_profiles_configuration(profiles_path: str):
    if not os.path.exists(profiles_path):
        return {}
    with open(profiles_path, "r") as f:
        return yaml.safe_load(f)
    