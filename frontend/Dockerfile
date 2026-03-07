FROM node:20-alpine

WORKDIR /app

ARG APP_ENV=development

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 3000

# Production: build then serve
# Development: hot-reload dev server
CMD if [ "$APP_ENV" = "production" ]; then \
      npm run build && npm start; \
    else \
      npm run dev; \
    fi
