FROM python:3.12
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /code
COPY requirements.txt /code/
RUN apt-get install -y libpq5
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY ./celery/start-celeryworker /start-celeryworker
RUN chmod +x /start-celeryworker

COPY ./celery/start-celerybeat /start-celerybeat
RUN chmod +x /start-celerybeat

COPY ./celery/start-flower /start-flower
RUN chmod +x /start-flower

USER 1000:1000
COPY website/ /code/
CMD ["daphne", "website.asgi:application", "-b", "::"]
