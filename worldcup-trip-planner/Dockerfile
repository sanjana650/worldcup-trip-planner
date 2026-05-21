FROM python:3.11-slim

# Install Node.js (needed for MongoDB MCP server)
RUN apt-get update && apt-get install -y nodejs npm

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8080
CMD ["python", "server.py"]