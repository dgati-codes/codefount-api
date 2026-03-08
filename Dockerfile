# ─────────────────────────────────────────────────────────────────────────────
# Dockerfile — CodeFount FastAPI Backend
#
# Spring Boot equivalent:
#   FROM eclipse-temurin:21-jre-alpine
#   COPY target/codefount-*.jar app.jar
#   ENTRYPOINT ["java","-jar","/app.jar"]
#
# Multi-stage build keeps the final image small (no build tools).
# ─────────────────────────────────────────────────────────────────────────────

# ── Stage 1: dependency install ───────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Install system deps for psycopg2 / bcrypt compile
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: runtime ──────────────────────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy source
COPY . .

# Non-root user — security best practice
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
USER appuser

EXPOSE 8000

# Uvicorn with multiple workers (≈ Spring Boot embedded Tomcat thread pool)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]