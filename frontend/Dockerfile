# Use Node.js 18 as base
FROM node:18-alpine AS builder

# Set working directory
WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install --frozen-lockfile
RUN npm install -D tailwindcss@3

# Copy rest of the project
COPY . .

# Set NODE_ENV to production
ENV NODE_ENV=development
ENV PORT=3000

EXPOSE 3000

# Start Next.js app
CMD ["npm", "run", "dev"]
