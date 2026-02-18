FROM python:3.11-slim

WORKDIR /app


RUN apt-get update && apt-get install -y tree && apt-get clean


COPY . .


RUN echo "=== CONTENU DU DOSSIER GTFS ===" && \
    tree static/downloads/ && \
    [ -f "static/downloads/gtfs_unifie.zip" ] || (echo "FICHIER GTFS MANQUANT!" && exit 1)


RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 10000
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:10000"]