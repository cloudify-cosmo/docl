#! /bin/bash -e

echo "host all all 0.0.0.0/32 md5" >> /var/lib/pgsql/9.5/data/pg_hba.conf
echo "listen_addresses = '*'" >> /var/lib/pgsql/9.5/data/postgresql.conf
