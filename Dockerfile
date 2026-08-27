FROM python:3.14-slim

WORKDIR /app
# Install locales and generate en_US.UTF-8
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y locales && \
    echo "en_US.UTF-8 UTF-8" > /etc/locale.gen && \
    locale-gen && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Переменные окружения — они будут действовать во время сборки и при запуске
ENV LANG=en_US.UTF-8 \
    LANGUAGE=en_US:en \
    LC_ALL=en_US.UTF-8


COPY requirements.txt requirements.txt
RUN pip install --no-deps --no-cache-dir -r requirements.txt \
    --index-url https://download.pytorch.org/whl/cpu \
    --extra-index-url https://pypi.org/simple

COPY . .

CMD [ "python","main.py" ]