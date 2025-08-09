FROM python:3.12-slim

# Install git for cloning repos
RUN apt-get update && apt-get install -y git

# Create a working directory
WORKDIR /app

# Install pytest (or any test dependencies you want globally)
RUN pip install pytest

# Default command
CMD ["pytest"]
