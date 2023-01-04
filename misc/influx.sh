docker run -d -p 8086:8086 \
      -v /var/lib/influxdb2:/var/lib/influxdb2 \
      --rm \
      influxdb:2.0
docker ps
