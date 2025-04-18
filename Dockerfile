FROM python:3.11-slim
WORKDIR /app
COPY index.html /app/index.html
EXPOSE 5000
CMD ["python3", "-m", "http.server", "5000"]