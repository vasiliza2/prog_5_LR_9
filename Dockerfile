FROM python:3.10-slim

WORKDIR /app

COPY req.txt req.txt
COPY . .

RUN pip install --no-cache-dir -r req.txt

EXPOSE 5001

CMD ["python", "main.py"]