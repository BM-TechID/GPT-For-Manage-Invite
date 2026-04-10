FROM python:3.10-alpine
WORKDIR /app
COPY . .
# Membuat file database default jika belum ada saat proses build
RUN echo "{}" > database.json 
CMD ["python", "server.py"]