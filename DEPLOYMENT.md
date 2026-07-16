# Karachi Flat Finder - 24/7 Cloud Deployment Guide

This guide explains how to deploy the project to **GitHub Actions** so it runs in the cloud 24/7, for free, even when your laptop is turned off.

---

## Step 1: Test Locally (Optional but Recommended)

Before deploying to the cloud, you can test if the email alerts work from your laptop:

1. Confirm that your `.env` file contains your credentials (copied from Maimoon Dental Care website):
   ```text
   EMAIL_USER=mbandookwala5253@gmail.com
   EMAIL_PASS=jksh bqka oepo xoac
   ```
2. Run the email testing script manually:
   ```bash
   venv\Scripts\activate
   python test_email.py
   ```
   If successful, a test email will be sent directly to your Gmail inbox!

---

## Step 2: Deploy to GitHub Actions (24/7 Cloud Run)

GitHub Actions will run your script in the cloud automatically.

1. **Create a Private GitHub Repository:**
   * Go to [GitHub](https://github.com/) and create a new repository.
   * Make it **Private** so that your property database and credentials remain secret.
2. **Upload Your Code:**
   Open a terminal in your project directory `C:\Users\mustafa bandookwala\.gemini\antigravity\scratch\karachi_flat_finder` and run:
   ```bash
   git init
   git add .
   git commit -m "initial commit"
   git branch -M main
   git remote add origin <your-github-repo-url>
   git push -u origin main
   ```
3. **Add Gmail Secrets to GitHub:**
   * Go to your GitHub repository in your browser.
   * Click **Settings > Secrets and variables > Actions**.
   * Click **New repository secret** and add the following 2 secrets:
     * Name: `EMAIL_USER` | Value: `mbandookwala5253@gmail.com`
     * Name: `EMAIL_PASS` | Value: `jksh bqka oepo xoac`
4. **Grant Write Permissions for Database Sync:**
   * In your GitHub repository, click **Settings > Actions > General**.
   * Scroll down to **Workflow permissions**.
   * Select **"Read and write permissions"** and check **"Allow GitHub Actions to create and approve pull requests"**.
   * Click **Save**.
   *(This allows the automated worker to push the updated `flats.json` file back to your repo so it doesn't send you duplicate emails on the next run!)*

---

## How It Works

* Every 2 hours, GitHub Actions will trigger your scraper in the cloud.
* It downloads OLX, Zameen, and Google search results, filters them, and compares them with the list of properties stored in your repository's `flats.json`.
* If a new property is found, its contact details are extracted in real-time, and a styled HTML email alert is delivered to your inbox (`mbandookwala5253@gmail.com`).
* The workflow commits the updated `flats.json` back to your GitHub repository to save it as "seen".
