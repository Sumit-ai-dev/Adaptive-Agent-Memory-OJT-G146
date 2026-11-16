# ==============================================================================
# Multi-stage Production Dockerfile for AEMA React Dashboard (Vite)
# Serves static assets via optimized Nginx with reverse proxy & SSE streaming
# ==============================================================================

# --- Stage 1: Build Static Assets ---
FROM node:22-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY tsconfig*.json vite.config.ts postcss.config.js tailwind.config.js index.html ./
COPY public ./public
COPY src ./src

RUN npm run build

# --- Stage 2: Production Nginx Server ---
FROM nginx:1.27-alpine AS runner

RUN rm -rf /usr/share/nginx/html/*

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD wget -qO- http://localhost/healthz || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
