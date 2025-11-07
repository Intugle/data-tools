# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Install uv for faster package installation
RUN pip install uv

# Install the intugle package
RUN uv pip install --system intugle

# Download NLTK data during the build process
RUN python -c "import nltk; nltk.download('words'); nltk.download('punkt'); nltk.download('stopwords')"

RUN mkdir -p models/
# Expose the port the app runs on
EXPOSE 8080

# Set environment variables for the MCP server
ENV PROJECT_BASE="models"
ENV MCP_SERVER_HOST="0.0.0.0"

# Command to run the application
CMD ["intugle-mcp"]