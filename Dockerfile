FROM python:3.11

# Устанавливаем Python
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    # МИНИМУМ графических библиотек
    libgl1 \
    && rm -rf /var/lib/apt/lists/*


WORKDIR /app

# Копируем requirements
COPY requirements.txt .

# Устанавливаем Python зависимости (используем opencv-python-headless)
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Создаем директории
RUN mkdir -p buildObj in out workdir data runs icons models readDicom static templates utils

# Копируем код
COPY . .

ENV PYTHONPATH=/app
ENV FLASK_APP=main_frontend.py

EXPOSE 5000
CMD ["python", "main_frontend.py"]