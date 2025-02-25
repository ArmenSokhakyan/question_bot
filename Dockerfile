# Use an official Python runtime as the base image
FROM python:3.12.3

# Set the working directory inside the container
WORKDIR /question_bot

# Copy requirements.txt first to leverage Docker cache for dependencies
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the port your app runs on
EXPOSE 5000

# Command to run the application
CMD ["python", "app:ain.py"]
