# Use the official Python 3.10 slim image as the base

FROM python:3.10-slim 
# Set the working directory inside the container to /app
WORKDIR /app

# Copy the requirements.txt file into the container at /app/
COPY agents/agent_a/requirements.txt /app/requirements.txt

# Install Python dependencies from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

#u Upgrade protobuf
RUN pip install --upgrade protobuf

# Copy the agent_a source code from the project root into /app
# This ensures all agent_a code is available in the container
COPY agents/agent_a /app

# Copy the shared 'common' directory (with protobufs and shared code) from the project root into /app/common
# This makes the 'common' package available for imports like 'from common.a2a_protocol.proto import a2a_message_pb2'
COPY common /app/common

# Set the PYTHONPATH so Python can find the common package
ENV PYTHONPATH=/app

# Set the default command to run the agent using unbuffered output (for real-time logs)
CMD ["python", "-u", "agent.py"]
