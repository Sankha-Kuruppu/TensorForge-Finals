FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

# CPU-only torch keeps the image small
RUN pip install torch==2.14.1 --index-url https://download.pytorch.org/whl/cpu
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY jobshield ./jobshield
COPY dashboard ./dashboard
COPY scripts ./scripts

# data download, splits and training happen at build time, so the image starts ready to serve
RUN python -m jobshield.data.prepare && python -m jobshield.train --version v1 --promote

EXPOSE 8000 8501
CMD ["bash", "scripts/start.sh"]
