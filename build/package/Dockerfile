FROM public.ecr.aws/lambda/microvms:al2023-minimal

WORKDIR /app

RUN dnf install -y python3 \
    && dnf clean all \
    && rm -rf /var/cache/dnf

COPY app.py /app/app.py

EXPOSE 8080

CMD ["python3", "/app/app.py"]