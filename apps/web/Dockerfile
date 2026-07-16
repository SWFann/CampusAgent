# Multi-stage build for Next.js application in a pnpm workspace

# Stage 1: Dependencies
FROM node:18-alpine AS deps
RUN apk add --no-cache libc6-compat
WORKDIR /app

# Copy pnpm workspace config and lock files from repo root
COPY pnpm-lock.yaml pnpm-workspace.yaml package.json ./

# Copy web package.json
COPY apps/web/package.json ./apps/web/

# Enable pnpm
RUN corepack enable pnpm

# Install dependencies (frozen lockfile for reproducibility)
RUN pnpm install --frozen-lockfile

# Stage 2: Builder
FROM node:18-alpine AS builder
WORKDIR /app

# Copy installed dependencies from deps stage
COPY --from=deps /app ./
RUN corepack enable pnpm

# Copy all web source files (respecting .dockerignore)
COPY apps/web/ ./apps/web/

# Set Next.js environment
ENV NEXT_TELEMETRY_DISABLED=1

# Build Next.js application
RUN pnpm --filter @campus-agent/web build

# Stage 3: Runner (production)
FROM node:18-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Create non-root user for security
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# Copy built application and node_modules
COPY --from=builder --chown=nextjs:nodejs /app ./

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# Start Next.js production server
CMD ["node", "apps/web/node_modules/.bin/next", "start", "--port", "3000", "--hostname", "0.0.0.0"]
