FROM ubuntu:latest

# Install dependencies
RUN apt-get update && \
    apt-get install -y \
    bash \
    python3 \
    python3-pip \
    python3-venv \
    openjdk-11-jdk \
    && apt-get clean


RUN  apt-get update &&  apt-get install -y wget unzip && \
     wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
     apt install -y ./google-chrome-stable_current_amd64.deb && \
     rm google-chrome-stable_current_amd64.deb && \
     apt-get clean

# Set the working directory inside the container
WORKDIR /app

# Create and activate virtual environment, and install Python dependencies in a single step
COPY requirements.txt ./requirements.txt
RUN python3 -m venv ./venv && \
    ./venv/bin/pip install --upgrade pip && \
    ./venv/bin/pip install -r ./requirements.txt

# Copy the rest of the application code into the container
COPY . .

HEALTHCHECK CMD curl --fail http://localhost:5000/v1/api/iserver/auth/status || exit 1
RUN chmod +x /app/starter.sh

RUN chmod +x /app/venv/bin/activate

# Set the default command to run the script
CMD ["/app/starter.sh"]
