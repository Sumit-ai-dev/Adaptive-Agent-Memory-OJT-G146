# Generated Dockerfile for AEMA MCP Server
# Multi-stage lightweight build for production execution
# Pinned to immutable multi-arch digest for OpenSSF Scorecard compliance
FROM node:22-alpine@sha256:947e5454e08bfe0b8ddda604915ad76275276c774f47da90d0137252c793a778 AS builder

WORKDIR /app

# Copy dependency manifests
COPY package.json tsconfig.json tsup.config.ts ./

# Install dependencies and build
RUN npm install
COPY src ./src
RUN npm run build

# --- Production Image ---
FROM node:22-alpine@sha256:947e5454e08bfe0b8ddda604915ad76275276c774f47da90d0137252c793a778 AS runner

WORKDIR /app
ENV NODE_ENV=production

# Copy built artifacts and production dependencies only
COPY package.json ./
RUN npm install --omit=dev

COPY --from=builder /app/dist ./dist
COPY README.md LICENSE ./

# Set non-root user for security best practices
USER node

ENTRYPOINT ["node", "dist/mcp.js"]
