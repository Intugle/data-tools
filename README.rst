=================
Data-Tools
=================

.. image:: https://img.shields.io/pypi/v/data-tools.svg
        :target: https://pypi.python.org/pypi/data-tools

.. image:: https://img.shields.io/travis/intugle/data-tools.svg
        :target: https://travis-ci.com/intugle/data-tools

.. image:: https://readthedocs.org/projects/data-tools/badge/?version=latest
        :target: https://data-tools.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status

.. image:: https://pyup.io/repos/github/intugle/data-tools/shield.svg
     :target: https://pyup.io/repos/github/intugle/data-tools/
     :alt: Updates


*Automated Data Profiling, Link Prediction, and Semantic Layer Generation*

Overview
--------

Data-Tools is a Python library that helps you automatically build a semantic layer over your data. It streamlines the process of data profiling, discovering relationships between tables, and generating a business-friendly representation of your data. This makes it easier for both data and business teams to understand and query data without needing to be SQL experts.

Who is this for?
----------------

This tool is designed for both **data teams** and **business teams**.

* **Data teams** can use it to automate data profiling, schema discovery, and documentation, significantly accelerating their workflow.
* **Business teams** can use it to gain a better understanding of their data and to perform self-service analytics without needing to write complex SQL queries.

Features
--------

* **Automated Data Profiling:** Generate detailed statistics for each column in your dataset, including distinct count, uniqueness, completeness, and more.
* **Datatype Identification:** Automatically identify the data type of each column (e.g., integer, string, datetime).
* **Key Identification:** Identify potential primary keys in your tables.
* **LLM-Powered Link Prediction:** Use a Large Language Model (LLM) to automatically discover relationships (foreign keys) between tables.
* **Business Glossary Generation:** Generate a business glossary for each column using an LLM, with support for industry-specific domains.
* **Semantic Layer Generation:** Create a `manifest.json` file that defines your semantic layer, inclpuding models (tables) and their relationships.
* **SQL Generation:** Generate SQL queries from the semantic layer, allowing you to query your data using business-friendly terms.
* **Extensible and Configurable:** Configure the tool to work with your specific environment and data sources.

Getting Started
---------------

**Prerequisites**

* Python 3.12+
* pip

**Installation**

   .. code-block:: bash

      pip install data-tools

**Configuration**

Before running the project, you need to configure a Large Language Model (LLM). This is used for tasks like generating business glossaries and predicting links between tables.

You can configure the LLM by setting the following environment variables:

* ``LLM_PROVIDER``: The LLM provider and model to use (e.g., ``openai:gpt-3.5-turbo``).
* ``OPENAI_API_KEY``: Your API key for the LLM provider.

Here's an example of how to set these variables in your environment:

.. code-block:: bash

   export LLM_PROVIDER="openai:gpt-3.5-turbo"
   export OPENAI_API_KEY="your-openai-api-key"

Quickstart
----------

For a detailed, hands-on introduction to the project, please see the `quickstart.ipynb <notebooks/quickstart.ipynb>`_ notebook. It will walk you through the entire process of profiling your data, predicting links, generating a semantic layer, and querying your data.

Usage
-----

The core workflow of the project involves the following steps:

1. **Load your data:** Load your data into pandas DataFrames.
2. **Create `DataSet` objects:** Create a `DataSet` object for each of your tables.
3. **Run the analysis pipeline:** Use the ``run()`` method to profile your data and generate a business glossary.
4. **Predict links:** Use the `LinkPredictor` to discover relationships between your tables.
5. **Generate the manifest:** Save the profiling and link prediction results to YAML files and then load them to create a `manifest.json` file.
6. **Generate SQL:** Use the `SqlGenerator` to generate SQL queries from the semantic layer.

For detailed code examples, please refer to the `quickstart.ipynb <quickstart.ipynb>`_ notebook.

Contributing
------------

Contributions are welcome! Please see the `CONTRIBUTING.md <CONTRIBUTING.md>`_ file for guidelines.

License
-------

This project is licensed under the MIT License. See the `LICENSE <LICENSE>`_ file for details.

