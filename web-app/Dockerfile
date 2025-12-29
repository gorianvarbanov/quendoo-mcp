# Multi-stage build for React frontend + Flask backend

# Stage 1: Build React app
FROM node:18-alpine as frontend-build

WORKDIR /app/frontend

# Copy package files from web-app directory
COPY web-app/package.json web-app/package-lock.json* ./

# Install dependencies
RUN npm install

# Copy source code from web-app directory
COPY web-app/public ./public
COPY web-app/src ./src

# Build React app
RUN npm run build

# Stage 2: Python Flask backend
FROM python:3.13-slim

WORKDIR /app

# Copy Python requirements from root directory
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Python backend code from root directory
COPY *.py ./
COPY tools ./tools

# Copy built React app from frontend stage
COPY --from=frontend-build /app/frontend/build ./static

# Expose port
EXPOSE 8080

# Set environment variables
ENV HOST=0.0.0.0
ENV PORT=8080
ENV FLASK_APP=stytch_server.py

# Run Flask server (serves both API and static React files)
CMD ["python", "stytch_server.py"]
