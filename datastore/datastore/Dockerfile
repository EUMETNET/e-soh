# useful commands:
# docker build --tag main . -f Dockerfile
# docker run -it main /bin/bash
# docker image ls
# docker image rm -f main
# ...

FROM golang:1.24-bookworm

ARG VERSION_GRPC_HEALTH_PROBE=v0.4.19

SHELL ["/bin/bash", "-eux", "-o", "pipefail", "-c"]

WORKDIR /app

# install protoc
RUN apt-get update \
    && apt-get -y upgrade \
    && apt-get install -y --no-install-recommends \
    protobuf-compiler libprotobuf-dev \
    # install protoc-gen-go
    && go install google.golang.org/protobuf/cmd/protoc-gen-go@latest \
    # install protoc-gen-go-grpc
    && go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest \
    # install grpc healtcheck service \
    && arch=$(echo "$(uname)-$(dpkg --print-architecture)" | tr '[:upper:]' '[:lower:]') \
    && wget -q --output-document "/bin/grpc_health_probe" "https://github.com/grpc-ecosystem/grpc-health-probe/releases/download/${VERSION_GRPC_HEALTH_PROBE}/grpc_health_probe-${arch}" \
    && chmod +x "/bin/grpc_health_probe" \
    # Cleanup
    && rm -rf /usr/tmp  \
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# copy source files, include via dockerignore
COPY . /go-grpc-demo

WORKDIR /go-grpc-demo

#ENTRYPOINT ["tail", "-f", "/dev/null"]

RUN \
    # compile proto file \
    protoc --go_out=. --go-grpc_out=. protobuf/datastore.proto \
    # fix dependencies
    && go mod tidy  \
    # build datastore server
    && go build -o dsserver main/main.go

CMD [ "./dsserver" ]
