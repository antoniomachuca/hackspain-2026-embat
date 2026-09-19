# Imagen del servicio "web". Railpack no conseguía construir este front, así
# que fijamos la receta a mano: Node 22 + npm ci + next build.
FROM node:22-slim

WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# El cliente lee la API desde NEXT_PUBLIC_API_URL, y Next la incrusta en el
# bundle durante el build: tiene que estar presente aquí, no solo en runtime.
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN npm run build

ENV NODE_ENV=production
EXPOSE 3000
CMD ["npm", "start"]
