FROM python:3.11-slim
WORKDIR /app

# Copy packages list first and install (Docker caching optimize karne ke liye)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy complete application files
COPY . .

EXPOSE 5000
CMD ["python", "app.py"]
