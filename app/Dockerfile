FROM public.ecr.aws/docker/library/python:3.10.14
# FROM python:3.10.14

WORKDIR /app

COPY requirements.txt ./

RUN pip install -r requirements.txt

COPY . .

EXPOSE 8080

CMD ["python", "-m", "flask", "--app", "main", "run", "--host=0.0.0.0", "-p", "8080"]
