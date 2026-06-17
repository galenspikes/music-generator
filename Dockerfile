# Stage 1: build the Vite frontend
FROM node:20-slim AS frontend-build
WORKDIR /build
COPY webapp/frontend/package*.json ./
RUN npm ci
COPY webapp/frontend/ ./
RUN npm run build

# Stage 2: Python API server
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
COPY --from=frontend-build /build/dist webapp/frontend/dist

# HF Spaces requires port 7860
EXPOSE 7860
ENV PYTHONPATH=/app
WORKDIR /app/webapp/backend
CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
