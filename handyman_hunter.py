name: Run Handyman Hunter Scraper

on:
  workflow_dispatch:
  schedule:
    - cron: '0 7,13,17 * * *'
      timezone: 'America/New_York'
    - cron: '30 8,20 * * *'
      timezone: 'America/New_York'

permissions:
  contents: write

jobs:
  run-scraper:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Repository Code
        uses: actions/checkout@v4

      - name: Set Up Python Environment
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'

      - name: Install Python Dependencies
        run: |
          python -m pip install --upgrade pip
          pip install requests feedparser geopy

      - name: Execute Scraper Script
        env:
          APIFY_TOKEN: ${{ secrets.APIFY_TOKEN }}
          OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
        run: python handyman_hunter.py

      - name: Automatically Commit and Push Updated Dashboard
        run: |
          git config --global user.name "GitHub Actions Automation"
          git config --global user.email "actions@github.com"
          git add dual_leads_history.json leads_dashboard.html || true
          if ! git diff-index --quiet HEAD --; then
            git commit -m "Auto-update: Expanded regional dashboard refreshed"
            git push origin HEAD:${{ github.ref_name }}
          fi
