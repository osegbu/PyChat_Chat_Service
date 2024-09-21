FROM python:3.10-slim

WORKDIR /src

COPY . .

RUN pip install  -r requirements.txt

EXPOSE 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]

