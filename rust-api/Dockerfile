# Cascabel Rust API Dockerfile
# Multi-stage build for optimized production image

# ============================================
# Stage 1: Build stage
# ============================================
FROM rust:1.75-slim-bookworm as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    pkg-config \
    libssl-dev \
    libproj-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy manifests first for layer caching
COPY Cargo.toml Cargo.lock* ./

# Create dummy main.rs to build dependencies
RUN mkdir src && \
    echo "fn main() {}" > src/main.rs && \
    echo "pub fn create_app() -> axum::Router { axum::Router::new() }" > src/lib.rs

# Build dependencies only (will be cached if Cargo.toml hasn't changed)
RUN cargo build --release && rm -rf src

# Copy actual source code
COPY src ./src

# Touch main.rs to invalidate the dummy build
RUN touch src/main.rs src/lib.rs

# Build the actual application
RUN cargo build --release

# ============================================
# Stage 2: Runtime stage
# ============================================
FROM debian:bookworm-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    ca-certificates \
    libssl3 \
    libproj25 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the built binary from builder stage
COPY --from=builder /app/target/release/cascabel-api /app/cascabel-api

# Create non-root user for security
RUN useradd -r -s /bin/false cascabel && \
    chown -R cascabel:cascabel /app

USER cascabel

# Expose the API port (8001 to avoid conflict with Python API on 8000)
EXPOSE 8001

# Set environment variables
ENV RUST_LOG=cascabel_api=info,tower_http=info

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Run the binary
CMD ["./cascabel-api"]
