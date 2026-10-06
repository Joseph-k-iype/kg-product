FROM python:3.12-slim
WORKDIR /app
COPY requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock --extra-index-url https://download.pytorch.org/whl/cpu
COPY . .
