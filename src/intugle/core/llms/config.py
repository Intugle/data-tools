def get_llm_config(config: dict, type: str = "azure"):
    if type.__eq__("azure"):
        deployment = {
            # "model":config["API_INFO"]["DEPLOYMENT_NAME"],
            "deployment_name": config["API_INFO"]["DEPLOYMENT_NAME"],
            "openai_api_version": config["API_INFO"]["API_VERSION"],
            "azure_endpoint": config["API_INFO"]["API_BASE"],
            "openai_api_key": config["API_INFO"]["API_KEY"],
        }

    elif type.__eq__("openai"):
        deployment = config["API_INFO"]
        # deployment = {
        #     "model_name":config["API_INFO"]["DEPLOYMENT_NAME"]
        # }
    else:
        raise ValueError("[!] Invalid model type")
    return deployment
