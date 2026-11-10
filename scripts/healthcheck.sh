#!/usr/bin/env bash

URL="$1"

if [ -z "$URL" ]; then 
    echo "Usage: $0 <URL>"
    exit 1
fi
for i in {1..5};do

    STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$URL/health")
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

    echo "[$TIMESTAMP] Attempt $i/5 - HTTP $STATUS"
    
    if [ "$STATUS" =  "200" ]; then
        echo "Application is healthy"
        exit 0
    fi
    if [ "$i" -lt 5 ]; then
    sleep 3
    fi
done
exit 1

