# -----------------------------
# Base Image (.NET 8 SDK - Ubuntu Jammy)
# -----------------------------
FROM mcr.microsoft.com/dotnet/sdk:8.0-jammy

# -----------------------------
# Install Minimal Utilities
# -----------------------------
RUN apt-get update && \
    apt-get install -y curl && \
    rm -rf /var/lib/apt/lists/*

# -----------------------------
# Create Non-Root User (Optional)
# -----------------------------
RUN useradd -m -u 1001 judgeuser

# -----------------------------
# Working Directory
# -----------------------------
WORKDIR /app

# -----------------------------
# Drop Privileges (Optional)
# -----------------------------
# USER judgeuser

# -----------------------------
# Default Command
# -----------------------------
CMD ["sleep", "300"]