#!/bin/bash
set -e

until pg_isready -h db -p 5432 -U repl_user; do
    sleep 2
done

if [ -z "$(ls -A "$PGDATA")" ]; then
    export PGPASSWORD='repl_password'
    pg_basebackup -h db -p 5432 -U repl_user -D "$PGDATA" -Fp -Xs -P -R
    chmod 0700 "$PGDATA"
fi
