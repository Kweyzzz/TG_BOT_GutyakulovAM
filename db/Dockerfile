FROM postgres:15

COPY init.sql /docker-entrypoint-initdb.d/01-init.sql
COPY init-replication.sh /docker-entrypoint-initdb.d/02-init-replication.sh

RUN chmod +x /docker-entrypoint-initdb.d/02-init-replication.sh
