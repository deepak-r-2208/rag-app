# --- Build stage -------------------------------------------------------
FROM node:20-alpine AS build
WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

# Vite bakes VITE_* vars in at build time, not runtime, so it's a build ARG.
# docker-compose.yml passes this automatically; override with
# `docker compose build --build-arg VITE_API_BASE_URL=...` if your backend
# lives somewhere other than http://localhost:8000.
ARG VITE_API_BASE_URL=http://localhost:8000
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN npm run build

# --- Serve stage ---------------------------------------------------------
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
