FROM node:20-alpine

WORKDIR /app

# Install dependencies first (better layer caching)
COPY package.json ./
RUN npm install --omit=dev

# Copy application code
COPY . .

# Ensure data + uploads directories exist (multer also creates uploads)
RUN mkdir -p /app/data /app/data/uploads

ENV PORT=3000 \
    NODE_ENV=production

EXPOSE 3000

CMD ["node", "server.js"]
