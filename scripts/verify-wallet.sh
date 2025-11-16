#!/bin/bash
# Verify wallet state and transactions

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ZecKit Faucet - Wallet Verification"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "1. Check wallet file in container:"
docker compose exec faucet cat /var/faucet/wallet.json | jq '.'

echo ""
echo "2. Check faucet stats:"
curl -s http://127.0.0.1:8080/stats | jq '.'

echo ""
echo "3. Check transaction history:"
curl -s http://127.0.0.1:8080/history | jq '.'

echo ""
echo "4. Check logs for transaction records:"
docker compose logs faucet | grep "Simulated send" | tail -5

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"