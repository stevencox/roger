FROM falkordb/falkordb-server:v4.14.4-alpine
# Remove Go if present (apk-installed or tarball)
RUN apk del --no-network go 2>/dev/null || true \
 && rm -rf /usr/local/go /usr/lib/go /root/go /go 2>/dev/null || true
RUN  apk add bash
