FROM node:20-alpine

WORKDIR /app
# for ts execution runtime
RUN npm install -g typescript
RUN npm install -g esbuild

RUN adduser -D sandbox
USER sandbox

CMD ["node"]
