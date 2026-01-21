#!/bin/bash
# Trigger dashboard update by making an empty commit
# This forces the GitHub Actions workflow to run

echo "Triggering dashboard update..."
git commit --allow-empty -m "trigger: force dashboard data update"
git push origin main
echo "Update triggered! Data will refresh in ~1 minute."
