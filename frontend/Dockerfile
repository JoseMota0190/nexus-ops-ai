# ============================================================
# Nexus Alarm — frontend (React + Vite) servido con nginx
# El build de Vite genera dist/ y nginx lo sirve + hace proxy de /api
# al backend (http://backend:8000) dentro de la red de docker compose.
#
# Importante: hace falta que exista package.json (lo genera el agente
# del frontend). Si todavía no existe, este build falla a propósito.
# ============================================================

# ---------- etapa 1: construir el frontend ----------
FROM node:20-alpine AS build
WORKDIR /app

# Manifest primero (mejor cache: solo reinstala si cambian las deps)
COPY package*.json ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

# Todo el código fuente del frontend
COPY . .

# URL del API en tiempo de build. Por defecto "/" (relativo) -> anda
# detrás del proxy de nginx. En Netlify se pasa VITE_API_URL al backend de Render.
ARG VITE_API_URL=/
ENV VITE_API_URL=${VITE_API_URL}

RUN npm run build

# ---------- etapa 2: servir con nginx ----------
FROM nginx:1.27-alpine
# Config de nginx: estático + proxy /api/ -> backend
COPY nginx.conf /etc/nginx/conf.d/default.conf
# Salida del build de Vite
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

# nginx oficial ya trae el CMD (nginx -g 'daemon off;')
