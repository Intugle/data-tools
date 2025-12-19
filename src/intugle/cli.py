import argparse
import importlib.util
import logging
import os
import subprocess
import sys

# Setup basic logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


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
    app_dir = os.path.join(os.path.dirname(__file__), "streamlit_app")
    app_path = os.path.join(app_dir, "main.py")

    # Ensure the app_path exists
    if not os.path.exists(app_path):
        print(f"Error: Streamlit app not found at {app_path}")
        return

    # Run the Streamlit app using subprocess, setting the working directory
    print(f"Launching Streamlit app from: {app_path} with working directory {app_dir}")
    subprocess.run(["streamlit", "run", app_path], cwd=app_dir)


def run_nosql_to_relational(args):
    """Execute the NoSQL to Relational conversion command."""
    # Import here to avoid issues when nosql dependencies aren't installed
    try:
        from intugle.nosql.api import NoSQLToRelationalParser
        from intugle.nosql.source import MongoSource
        from intugle.nosql.writer import ParquetTarget
    except ImportError as e:
        logger.error(
            "NoSQL dependencies not installed. Install with: pip install 'intugle[nosql]'"
        )
        logger.error(f"Missing: {e}")
        sys.exit(1)

    try:
        logger.info(f"Connecting to MongoDB: {args.db}.{args.collection}")
        source = MongoSource(
            uri=args.uri,
            database=args.db,
            collection=args.collection,
            sample_size=args.sample,
        )

        logger.info("Initializing parser...")
        # Initialize orchestrator
        orchestrator = NoSQLToRelationalParser(source)

        # Run parsing
        logger.info("Starting extraction and parsing...")
        orchestrator.run()

        # Write output
        logger.info(f"Writing results to: {args.output}")
        target = ParquetTarget(args.output)
        orchestrator.write(target)

        logger.info("✅ Job completed successfully!")

    except Exception as e:
        logger.error(f"Job failed: {str(e)}")
        sys.exit(1)


def main():
    """Main entry point for the intugle CLI."""
    parser = argparse.ArgumentParser(
        description="Intugle - GenAI-powered semantic layer toolkit"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Define the 'streamlit' command
    subparsers.add_parser("streamlit", help="Launch the Streamlit web application")

    # Define the 'nosql-to-relational' command
    nosql_parser = subparsers.add_parser(
        "nosql-to-relational", help="Convert NoSQL collection to Parquet"
    )

    # Source Arguments
    nosql_parser.add_argument("--uri", required=True, help="MongoDB connection URI")
    nosql_parser.add_argument("--db", required=True, help="Database name")
    nosql_parser.add_argument("--collection", required=True, help="Collection name")

    # Output Arguments
    nosql_parser.add_argument(
        "--output", required=True, help="Output directory for Parquet files"
    )

    # Optional Arguments
    nosql_parser.add_argument(
        "--sample",
        type=int,
        default=0,
        help="Number of documents to sample (0 = all)",
    )

    args = parser.parse_args()

    if args.command == "streamlit":
        run_streamlit_app()
    elif args.command == "nosql-to-relational":
        run_nosql_to_relational(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

