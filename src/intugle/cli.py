import argparse
import importlib.util
import json
import logging
import os
import subprocess
import sys

# Setup basic logging for CLI commands
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
    app_dir = os.path.join(os.path.dirname(__file__), 'streamlit_app')
    app_path = os.path.join(app_dir, 'main.py')

    # Ensure the app_path exists
    if not os.path.exists(app_path):
        print(f"Error: Streamlit app not found at {app_path}")
        return

    # Run the Streamlit app using subprocess, setting the working directory
    print(f"Launching Streamlit app from: {app_path} with working directory {app_dir}")
    subprocess.run(["streamlit", "run", app_path], cwd=app_dir)


def run_text_to_semantic(args):
    """Execute the text-to-semantic conversion command."""
    try:
        from intugle.text_processor import TextToSemanticProcessor
    except ImportError as e:
        logger.error("Text processor not available.")
        logger.error(f"Error: {e}")
        sys.exit(1)

    try:
        # Read input text
        if args.input == "-":
            text = sys.stdin.read()
        else:
            with open(args.input, "r", encoding="utf-8") as f:
                text = f.read()

        logger.info(f"Processing text of length {len(text)} characters")

        # Initialize processor
        processor = TextToSemanticProcessor(
            model=args.model,
            output_format=args.format,
        )

        # Parse text to RDF
        logger.info("Extracting entities and relationships...")
        rdf_graph = processor.parse(text)

        logger.info(
            f"Extracted {len(rdf_graph.entities)} entities, "
            f"{len(rdf_graph.relationships)} relationships, "
            f"{len(rdf_graph.triples)} triples"
        )

        # Output results
        if args.output_format == "turtle":
            output = rdf_graph.to_turtle()
        elif args.output_format == "json-ld":
            output = json.dumps(rdf_graph.to_json_ld(), indent=2)
        else:  # json
            output = json.dumps(rdf_graph.to_dict(), indent=2)

        if args.output:
            os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output)
            logger.info(f"Output written to: {args.output}")
        else:
            print(output)

        logger.info("Text-to-semantic conversion complete.")

    except Exception as e:
        logger.error(f"Job failed: {str(e)}")
        sys.exit(1)


def main():
    """Main entry point for the intugle CLI."""
    parser = argparse.ArgumentParser(
        description="Intugle - GenAI-powered semantic layer toolkit"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Streamlit command
    subparsers.add_parser("streamlit", help="Launch the Streamlit web application")

    # Text-to-semantic command
    text_parser = subparsers.add_parser(
        "text-to-semantic", help="Convert unstructured text to RDF/semantic triples"
    )
    text_parser.add_argument(
        "--input", "-i", required=True,
        help="Input text file path (use '-' for stdin)"
    )
    text_parser.add_argument(
        "--output", "-o",
        help="Output file path (prints to stdout if not specified)"
    )
    text_parser.add_argument(
        "--model", "-m", default="gpt-4o-mini",
        help="LLM model for extraction (default: gpt-4o-mini)"
    )
    text_parser.add_argument(
        "--format", "-f", choices=["rdf", "rdf_star"], default="rdf_star",
        help="RDF format: 'rdf' or 'rdf_star' (default: rdf_star)"
    )
    text_parser.add_argument(
        "--output-format", choices=["json", "turtle", "json-ld"], default="json",
        help="Output format: json, turtle, or json-ld (default: json)"
    )

    args = parser.parse_args()

    if args.command == "streamlit":
        run_streamlit_app()
    elif args.command == "text-to-semantic":
        run_text_to_semantic(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

