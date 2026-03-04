#!/bin/bash

GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

SERVER_PORT=${SERVER_PORT:-4000}
CLIENT_PORT=${CLIENT_PORT:-5183}

echo -e "${YELLOW}Stopping Observability Dashboard...${NC}"

for port in $SERVER_PORT $CLIENT_PORT; do
    if [[ "$OSTYPE" == "darwin"* ]]; then
        PIDS=$(lsof -ti :"$port" 2>/dev/null)
    else
        PIDS=$(lsof -ti :"$port" 2>/dev/null || fuser -n tcp "$port" 2>/dev/null | awk '{for (i=2; i<=NF; i++) print $i}')
    fi

    if [ -n "$PIDS" ]; then
        for PID in $PIDS; do
            kill -9 $PID 2>/dev/null && echo -e "${GREEN}Killed process $PID on port $port${NC}"
        done
    else
        echo -e "${YELLOW}No process on port $port${NC}"
    fi
done

echo -e "${GREEN}Observability Dashboard stopped${NC}"
