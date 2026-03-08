# --- Build frontend ---
FROM node:22-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- Production ---
FROM python:3.12-slim
WORKDIR /app

# Install Python deps
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend
COPY backend/ ./backend/

# Copy built frontend
COPY --from=frontend-build /app/frontend/dist ./static/

# Serve static files from FastAPI
RUN echo 'from backend.main import app\nfrom fastapi.staticfiles import StaticFiles\nfrom fastapi.responses import FileResponse\nimport os\n\nstatic_dir = os.path.join(os.path.dirname(__file__), "static")\nif os.path.exists(static_dir):\n    @app.get("/")\n    async def index():\n        return FileResponse(os.path.join(static_dir, "index.html"))\n    app.mount("/", StaticFiles(directory=static_dir), name="static")' > serve.py

EXPOSE 8888

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8888"]
