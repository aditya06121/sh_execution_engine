FROM node:20-alpine

WORKDIR /app

RUN adduser -D sandbox
USER sandbox

CMD ["node"]
