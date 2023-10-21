# Use an official Python runtime as a parent image
FROM python:3.11

# Set environment variables
ENV PYTHONUNBUFFERED 1
ENV DJANGO_SETTINGS_MODULE django_project.settings

# Create and set the working directory
WORKDIR /app

# Copy only the requirements file and install dependencies
COPY requirements_docker.txt /app/

# Copy the current directory contents into the container at /app
COPY . /app/

RUN pip install --upgrade pip setuptools wheel

RUN pip install -r requirements_docker.txt

# Expose the port your application will run on
EXPOSE 8000

# Run the collectstatic command to collect static files
# RUN python manage.py collectstatic --noinput

# Start the Django development server
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
