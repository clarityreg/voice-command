#!/bin/bash

echo "Starting Observability Dashboard"
echo "================================"

GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

SERVER_PORT=${SERVER_PORT:-4000}
CLIENT_PORT=${CLIENT_PORT:-5183}

echo -e "${BLUE}Configuration:${NC}"
echo -e "  Server Port: ${GREEN}$SERVER_PORT${NC}"
echo -e "  Client Port: ${GREEN}$CLIENT_PORT${NC}"

# Kill processes on a port
kill_port() {
    local port=$1
    local name=$2

    echo -e "\n${YELLOW}Checking for existing $name on port $port...${NC}"

    if [[ "$OSTYPE" == "darwin"* ]]; then
        PIDS=$(lsof -ti :$port 2>/dev/null)
    else
        PIDS=$(lsof -ti :$port 2>/dev/null || fuser -n tcp $port 2>/dev/null | awk '{print $2}')
    fi

    if [ -n "$PIDS" ]; then
        echo -e "${RED}Found existing processes on port $port: $PIDS${NC}"
        for PID in $PIDS; do
            kill -9 $PID 2>/dev/null && echo -e "${GREEN}Killed process $PID${NC}" || echo -e "${RED}Failed to kill process $PID${NC}"
        done
        sleep 1
    else
        echo -e "${GREEN}Port $port is available${NC}"
    fi
}

kill_port $SERVER_PORT "server"
kill_port $CLIENT_PORT "client"

# Start server
echo -e "\n${GREEN}Starting server on port $SERVER_PORT...${NC}"
cd "$PROJECT_ROOT/apps/server"
SERVER_PORT=$SERVER_PORT bun run dev &
SERVER_PID=$!

# Wait for server health
echo -e "${YELLOW}Waiting for server to start...${NC}"
for i in {1..10}; do
    if curl -s http://localhost:$SERVER_PORT/health >/dev/null 2>&1; then
        echo -e "${GREEN}Server is ready!${NC}"
        break
    fi
    sleep 1
done

# Start client
echo -e "\n${GREEN}Starting client on port $CLIENT_PORT...${NC}"
cd "$PROJECT_ROOT/apps/client"
VITE_PORT=$CLIENT_PORT bun run dev &
CLIENT_PID=$!

# Wait for client
echo -e "${YELLOW}Waiting for client to start...${NC}"
for i in {1..10}; do
    if curl -s http://localhost:$CLIENT_PORT >/dev/null 2>&1; then
        echo -e "${GREEN}Client is ready!${NC}"
        break
    fi
    sleep 1
done

echo -e "\n${BLUE}========================================${NC}"
echo -e "${GREEN}Observability Dashboard Started${NC}"
echo -e "${BLUE}========================================${NC}"
echo
echo -e "Dashboard: ${GREEN}http://localhost:$CLIENT_PORT${NC}"
echo -e "Server:    ${GREEN}http://localhost:$SERVER_PORT${NC}"
echo -e "WebSocket: ${GREEN}ws://localhost:$SERVER_PORT/stream${NC}"
echo
echo -e "Server PID: ${YELLOW}$SERVER_PID${NC}"
echo -e "Client PID: ${YELLOW}$CLIENT_PID${NC}"
echo
echo -e "Stop with: ${YELLOW}./scripts/stop-observability.sh${NC}"
echo -e "${BLUE}Press Ctrl+C to stop both processes${NC}"

cleanup() {
    echo -e "\n${YELLOW}Shutting down...${NC}"
    kill $SERVER_PID 2>/dev/null
    kill $CLIENT_PID 2>/dev/null
    echo -e "${GREEN}Stopped all processes${NC}"
    exit 0
}

trap cleanup INT

wait $SERVER_PID $CLIENT_PID
