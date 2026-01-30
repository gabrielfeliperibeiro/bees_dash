#!/bin/bash

# BEES Dashboard - Manual Update Trigger
# Run this script to manually update dashboard data immediately

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🐝 BEES Dashboard - Manual Update"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo "❌ Error: GitHub CLI (gh) is not installed"
    echo "   Install: https://cli.github.com/"
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo "❌ Error: Not authenticated with GitHub CLI"
    echo "   Run: gh auth login"
    exit 1
fi

echo "📊 Triggering workflow..."
gh workflow run update-dashboard.yml

echo "⏳ Waiting for workflow to start..."
sleep 5

# Get the latest run
latest_run=$(gh run list --workflow=update-dashboard.yml --limit 1 --json databaseId --jq '.[0].databaseId')

if [ -z "$latest_run" ]; then
    echo "❌ Error: Could not find workflow run"
    exit 1
fi

echo "✅ Workflow triggered! Run ID: $latest_run"
echo ""
echo "🔍 Monitoring progress..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Monitor the run
max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
    run_info=$(gh run view $latest_run --json status,conclusion 2>/dev/null || echo '{"status":"unknown","conclusion":""}')
    status=$(echo "$run_info" | jq -r '.status')
    conclusion=$(echo "$run_info" | jq -r '.conclusion')

    if [ "$status" = "completed" ]; then
        echo ""
        if [ "$conclusion" = "success" ]; then
            echo "✅ SUCCESS! Data updated successfully"
            echo ""
            echo "📈 Latest data:"

            # Show latest data if files exist
            if [ -f "data/ph.json" ]; then
                ph_orders=$(cat data/ph.json | jq -r '.today.orders')
                ph_gmv=$(cat data/ph.json | jq -r '.today.total_gmv_usd')
                echo "   🇵🇭 Philippines: $ph_orders orders, \$$ph_gmv USD"
            fi

            if [ -f "data/vn.json" ]; then
                vn_orders=$(cat data/vn.json | jq -r '.today.orders')
                vn_gmv=$(cat data/vn.json | jq -r '.today.total_gmv_usd')
                echo "   🇻🇳 Vietnam: $vn_orders orders, \$$vn_gmv USD"
            fi

            echo ""
            echo "🌐 Dashboard will update in ~5-15 minutes (GitHub Pages)"
            echo ""
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            exit 0
        else
            echo "❌ FAILED! Workflow completed with status: $conclusion"
            echo ""
            echo "📋 View logs:"
            echo "   gh run view $latest_run --log-failed"
            echo ""
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            exit 1
        fi
    fi

    echo -ne "\r⏳ Status: $status... (${attempt}s)  "
    sleep 5
    ((attempt++))
done

echo ""
echo "⚠️  Timeout waiting for workflow (still running)"
echo "   Check status: gh run view $latest_run"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
