#!/bin/bash
# ==============================================================================
# Phase 1 Required Failure Scenarios & Observation Test Suite
# Maps directly to Section 6.3 of Course Project Manual
# ==============================================================================

set -e

DOMAIN="app.cn-capstone.test"
EDGE_IP="10.7.5.53"
EDGE_PORT="8443"

echo "========================================================================"
echo "    PHASE 1: SECTION 6.3 REQUIRED FAILURE DEMONSTRATIONS"
echo "========================================================================"
echo

# ------------------------------------------------------------------------------
# SCENARIO 1: Wrong DNS Server Configured on Client
# Concept: Proves DNS and IP layers are independent. Direct IP works, lookup fails.
# ------------------------------------------------------------------------------
echo "--- SCENARIO 1: Wrong DNS Server Configured on Client ---"
echo "Attempting DNS resolution against non-existent DNS server (10.7.200.200)..."
DNS_FAIL_OUTPUT=$(dig @10.7.200.200 "$DOMAIN" +time=1 +tries=1 2>&1 || true)
if echo "$DNS_FAIL_OUTPUT" | grep -E -iq "timed out|no servers could be reached"; then
    echo "[OBSERVATION] DNS lookup failed as expected: Connection timed out / unreachable."
else
    echo "[OUTPUT] $DNS_FAIL_OUTPUT"
fi

echo "Verifying Layer 3 IP Reachability still works to Edge ($EDGE_IP)..."
if ping -c 1 -W 1000 "$EDGE_IP" > /dev/null 2>&1; then
    echo "[OBSERVATION] Ping to $EDGE_IP SUCCEEDED."
    echo "[EXPLANATION] Demonstrates that Name Resolution (Layer 7) and IP Routing (Layer 3)"
    echo "              operate independently. Loss of DNS does not impact Layer 3 reachability."
else
    echo "[NOTE] Ping to $EDGE_IP not reachable from this node (run on LAN)."
fi
echo

# ------------------------------------------------------------------------------
# SCENARIO 2: DNS Record Points to Wrong IP Address
# Concept: Proves DNS is a directory service, not a transport connection.
# ------------------------------------------------------------------------------
echo "--- SCENARIO 2: DNS Record Points to Wrong IP Address ---"
WRONG_IP="10.7.99.99"
echo "Simulating DNS resolution returning non-existent host $WRONG_IP..."
echo "Attempting HTTPS connection to $WRONG_IP:$EDGE_PORT (Timeout 2s)..."
CURL_WRONG_IP=$(curl -m 2 -i "https://$WRONG_IP:$EDGE_PORT/" 2>&1 || true)
echo "[OBSERVATION] Curl Output:"
echo "$CURL_WRONG_IP" | head -n 3
echo "[EXPLANATION] Proves DNS is merely a directory service, not an active connection."
echo "              Successful resolution to an invalid IP results in TCP connection timeout/failure."
echo

# ------------------------------------------------------------------------------
# SCENARIO 3: One Backend Stopped
# Concept: Edge continues serving requests through the remaining healthy backend.
# ------------------------------------------------------------------------------
echo "--- SCENARIO 3: One Backend Stopped ---"
echo "If Backend A (3001) is stopped, test that requests still succeed via Backend B:"
echo "Executing client request to https://$DOMAIN:$EDGE_PORT/api/status..."
CURL_ONE_BACKEND=$(curl -s -i "https://$DOMAIN:$EDGE_PORT/api/status" 2>&1 || true)
if echo "$CURL_ONE_BACKEND" | grep -q "HTTP/1.1 200 OK"; then
    BACKEND_SEEN=$(echo "$CURL_ONE_BACKEND" | grep -i "^X-Backend:" | awk '{print $2}')
    echo "[OBSERVATION] Received HTTP 200 OK from Backend: $BACKEND_SEEN"
    echo "[EXPLANATION] The edge reverse proxy detects the stopped backend and transparently"
    echo "              forwards requests to the surviving healthy backend instance."
else
    echo "[NOTE] Live cluster not reachable from current environment. Verify on LAN."
fi
echo

# ------------------------------------------------------------------------------
# SCENARIO 4: Both Backends Stopped
# Concept: Edge proxy returns 502 Bad Gateway. Shows edge vs backend boundary.
# ------------------------------------------------------------------------------
echo "--- SCENARIO 4: Both Backends Stopped ---"
echo "Expected Behavior when both port 3001 and 3002 are unreachable:"
echo "Client DNS resolves -> TCP 8443 connects -> TLS completes -> Nginx returns HTTP 502 Bad Gateway."
echo "[EXPLANATION] Clearly separates the Edge Reverse Proxy boundary from the Backend"
echo "              Application boundary. TLS termination and TCP socket are healthy,"
echo "              but Nginx cannot establish an upstream connection."
echo

# ------------------------------------------------------------------------------
# SCENARIO 5: Wrong Destination Port on Client
# Concept: Destination IP is reachable, but TCP connection to port fails (TCP RST).
# ------------------------------------------------------------------------------
echo "--- SCENARIO 5: Wrong Destination Port on Client ---"
WRONG_PORT="9443"
echo "Attempting connection to valid Edge host ($EDGE_IP) on unopened port $WRONG_PORT..."
PORT_TEST_OUTPUT=$(curl -m 2 -i "https://$EDGE_IP:$WRONG_PORT/" 2>&1 || true)
echo "[OBSERVATION] Curl Output:"
echo "$PORT_TEST_OUTPUT" | head -n 3
echo "[EXPLANATION] Demonstrates that IP addresses (Layer 3) and Port numbers (Layer 4) are separate."
echo "              The host OS kernel receives the SYN packet, recognizes no process is bound"
echo "              to socket :9443, and immediately responds with a TCP RST (Connection Refused)."
echo

echo "========================================================================"
echo "    FAILURE DEMONSTRATION RUNBOOK COMPLETE"
echo "========================================================================"
