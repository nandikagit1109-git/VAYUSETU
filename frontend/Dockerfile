FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Vite dev-server proxies /api to the backend container.
ENV VITE_PROXY_TARGET=http://backend:8000

# Vite's dependency optimizer writes node_modules/.vite at startup, so the
# runtime user needs ownership; node:20-alpine ships the `node` user.
RUN chown -R node:node /app
USER node

EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
