# مرحله ساخت
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
RUN npm run build

# مرحله سرو با Nginx
FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.panel.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
