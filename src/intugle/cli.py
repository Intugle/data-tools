import importlib.util
import os
import subprocess


def run_streamlit_app():
    # A list of the required packages for the Streamlit app to run.
    # These correspond to the dependencies in the `[project.optional-dependencies].streamlit` section of pyproject.toml.
    required_modules = {
        "streamlit": "streamlit",
        "pyngrok": "pyngrok",
        "dotenv": "python-dotenv",
        "xlsxwriter": "xlsxwriter",
        "plotly": "plotly",
        "graphviz": "graphviz",
    }

    missing_modules = []
    for module_name, package_name in required_modules.items():
        if not importlib.util.find_spec(module_name):
            missing_modules.append(package_name)

    if missing_modules:
        print("Error: The Streamlit app is missing required dependencies.")
        print("The following packages are not installed:", ", ".join(missing_modules))
        print("\nTo use the Streamlit app, please install 'intugle' with the 'streamlit' extra:")
        print("  pip install 'intugle[streamlit]'")
        return

    # Get the absolute path to the main.py of the Streamlit app
    app_dir = os.path.join(os.path.dirname(__file__), 'streamlit_app')
    app_path = os.path.join(app_dir, 'main.py')
    
    # Ensure the app_path exists
    if not os.path.exists(app_path):
        print(f"Error: Streamlit app not found at {app_path}")
        return

    # Run the Streamlit app using subprocess, setting the working directory
    print(f"Launching Streamlit app from: {app_path} with working directory {app_dir}")
    subprocess.run(["streamlit", "run", app_path], cwd=app_dir)


if __name__ == "__main__":
    run_streamlit_app()
