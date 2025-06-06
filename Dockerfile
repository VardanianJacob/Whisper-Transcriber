# 📦 Base image with Python 3.11
FROM python:3.11

# 🏠 Set working directory inside the container
WORKDIR /app

# 📋 Copy dependencies and install them
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 📁 Copy the entire project into the container
COPY . .

# 🚀 Start the FastAPI server with Uvicorn
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080"]
