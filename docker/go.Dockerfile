# -----------------------------
# Base Image (Go 1.22 Alpine)
# -----------------------------
FROM golang:1.22-alpine

# Install minimal tools
RUN apk add --no-cache bash

# Create non-root user
RUN adduser -D runner
#USER runner

WORKDIR /app