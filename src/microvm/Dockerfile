FROM public.ecr.aws/lambda/microvms:al2023-minimal

WORKDIR /app

# Instala Python, Docker e ferramentas de desenvolvimento.
RUN dnf install -y \
        python3 \
        python3-pip \
        docker \
        git \
        zip \
        unzip \
        tar \
        gzip \
        findutils \
        procps-ng \
        shadow-utils \
    && dnf clean all \
    && rm -rf /var/cache/dnf

# Instala o AWS SAM CLI em um ambiente virtual isolado.
RUN python3 -m venv /opt/sam-cli \
    && /opt/sam-cli/bin/python -m pip install --upgrade pip \
    && /opt/sam-cli/bin/pip install aws-sam-cli \
    && ln -s /opt/sam-cli/bin/sam /usr/local/bin/sam

COPY app.py /app/app.py
COPY start.sh /usr/local/bin/start.sh

RUN chmod +x /usr/local/bin/start.sh \
    && mkdir -p /var/lib/docker /var/run/docker

EXPOSE 8080

CMD ["/usr/local/bin/start.sh"]
