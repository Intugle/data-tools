import os
import subprocess


def run_streamlit_app():
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
