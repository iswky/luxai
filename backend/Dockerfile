FROM python:3.11

WORKDIR /app

# install system dependencies for playwright
RUN apt-get update && apt-get install -y \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    && rm -rf /var/lib/apt/lists/*

# context is root
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# install playwright browsers
RUN playwright install chromium

# copy backend directory
COPY backend/ .

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
