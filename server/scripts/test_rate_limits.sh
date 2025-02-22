#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo "Testing Rate Limits"
echo "==================="

# Test authentication rate limit
echo -e "\n${GREEN}Testing Authentication Rate Limit (5 requests/minute)${NC}"
echo "Sending 6 login requests..."

for i in {1..6}; do
    response=$(curl -s -w "\n%{http_code}" -X POST http://localhost:8000/api/v1/auth/token \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=test@example.com&password=testpassword123")

    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')

    echo -e "\nRequest $i:"
    if [ "$http_code" == "200" ]; then
        echo -e "${GREEN}Success${NC} (HTTP 200)"
    elif [ "$http_code" == "429" ]; then
        echo -e "${RED}Rate Limited${NC} (HTTP 429)"
        echo "Response: $body"
    else
        echo -e "${RED}Error${NC} (HTTP $http_code)"
        echo "Response: $body"
    fi

    sleep 1
done

# Get token for API tests
echo -e "\n${GREEN}Getting token for API tests...${NC}"
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/token \
-H "Content-Type: application/x-www-form-urlencoded" \
-d "username=test@example.com&password=testpassword123" | jq -r .access_token)

if [ -z "$TOKEN" ]; then
    echo -e "${RED}Failed to get token. Exiting.${NC}"
    exit 1
fi

# Test standard API rate limit
echo -e "\n${GREEN}Testing Standard API Rate Limit${NC}"
echo "Sending requests to /me endpoint..."

for i in {1..61}; do
    response=$(curl -s -w "\n%{http_code}" -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/auth/me)

    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')

    echo -n "."
    if [ "$http_code" == "429" ]; then
        echo -e "\n${RED}Rate Limited${NC} after $i requests"
        echo "Response: $body"
        break
    fi

    sleep 0.1
done

echo -e "\n\n${GREEN}Rate Limit Testing Complete${NC}"
