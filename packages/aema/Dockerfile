# ==============================================================================
# Multi-stage Production Dockerfile for AEMA MCP Server (Node.js)
# Pinned to reproducible multi-arch base with OpenSSF Scorecard compliance
# ==============================================================================

# --- Stage 1: Build Stage ---
FROM node:22-alpine@sha256:947e5454e08bfe0b8ddda604915ad76275276c774f47da90d0137252c793a778 AS builder

WORKDIR /app

# Copy package manifests for reproducible dependency caching
COPY package.json package-lock.json tsconfig.json tsup.config.ts ./
RUN npm ci

COPY src ./src
RUN npm run build

# --- Stage 2: Production Hardened Runner ---
FROM node:22-alpine@sha256:947e5454e08bfe0b8ddda604915ad76275276c774f47da90d0137252c793a778 AS runner

WORKDIR /app
ENV NODE_ENV=production

COPY package.json package-lock.json ./
RUN npm ci --omit=dev && npm cache clean --force

COPY --from=builder /app/dist ./dist
COPY README.md LICENSE ./

# Enforce least-privilege non-root execution
USER node

ENTRYPOINT ["node", "dist/mcp.js"]
