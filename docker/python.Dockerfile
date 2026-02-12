FROM python:3.11-slim

WORKDIR /app

# Add non-root user (important even now)
RUN useradd -m judgeuser
USER judgeuser

CMD ["sleep", "300"]
