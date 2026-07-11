# Stage 1: Build the React frontend
FROM node:18-alpine AS frontend-builder
WORKDIR /app/webapp
COPY webapp/package*.json ./
RUN npm install
COPY webapp/ ./
# Build the frontend with relative API URL
ENV VITE_API_URL=/api
RUN npm run build

# Stage 2: Build the FastAPI backend and serve frontend
FROM python:3.10-slim
WORKDIR /app/backend

# Install python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ .

# Copy built frontend from Stage 1
COPY --from=frontend-builder /app/webapp/dist /app/webapp/dist

# Start FastAPI server
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
