# Summarize URLs in Slack messages using Gemini
[![MIT](https://img.shields.io/github/license/danishi/textlint-rule-gc-product-name)](https://github.com/danishi/slack-url-summarize-gemini/blob/main/LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat-square)](https://makeapullrequest.com)

A Slack bot that summarizes URLs shared in Slack channels using Google Cloud Functions (Cloud Run function 1st gen) and Vertex AI Gemini model.

![demo](https://github.com/user-attachments/assets/d7009994-3f27-4c8b-af33-2efe1f46846c)

## Table of Contents


- [Features](#features)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
- [Configuration](#configuration)
- [Deployment](#deployment)
- [Slack App Setup](#slack-app-setup)
- [License](#license)
- [Acknowledgments](#acknowledgments)

## Features

- Automatically summarizes articles from shared URLs in Slack.
- Extracts important keywords and generates a summary.
- Integrates with Google Cloud Functions and Vertex AI.

## Architecture

- **Slack Bot**: Built using the `slack_bolt` framework.
- **Google Cloud Functions**: Hosts the bot's backend logic.
- **Vertex AI**: Uses the Gemini 1.5 Flash model for text summarization.
- **Dependencies**: Managed via `requirements.txt`.

## Prerequisites

- **Google Cloud Platform (Google Cloud) Account** with billing enabled.
- **Slack Workspace** where you have permission to install apps.
- **Python 3.8+** installed locally for development.
- **Google Cloud SDK** installed and configured with your account.

## Setup

### 1. Clone the Repository

```bash
git clone https://github.com/danishi/slack-url-summarize-gemini.git
cd url-summarizer-slack-bot
```

### 2. Install Dependencies

Create a virtual environment and install the required packages:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Configuration

### 1. Environment Variables

Create a `.env` file in the root directory and add the following environment variables:

```dotenv
SLACK_BOT_TOKEN=your-slack-bot-token
SLACK_SIGNING_SECRET=your-slack-signing-secret
SLACK_REACTION_KEY=the-reaction-keyword
SLACK_PROCESSING_REACTION_KEY=the-processing-reaction-keyword
GOOGLE_CLOUD_PROJECT=your-Google Cloud-project-id
GOOGLE_CLOUD_LOCATION=asia-northeast1
GOOGLE_MODEL_NAME=gemini-1.5-flash-001
```

- **SLACK_BOT_TOKEN**: Obtain this from Slack after installing your app.
- **SLACK_SIGNING_SECRET**: Found in your Slack app's Basic Information page.
- **SLACK_REACTION_KEY**: The emoji name that triggers the bot (e.g., `summarize`).
- **SLACK_PROCESSING_REACTION_KEY**: The emoji name that processing the bot (e.g., `processing`).
- **GOOGLE_CLOUD_PROJECT**: Your Google Cloud project ID.
- **GOOGLE_CLOUD_LOCATION**: The location of your Google Cloud resources (e.g., `asia-northeast1`).
- **GOOGLE_MODEL_NAME**: The gen AI model name (e.g., `gemini-1.5-flash-001`).

### 2. Vertex AI Setup

Ensure that the Vertex AI API is enabled in your Google Cloud project and you have the necessary permissions.

## Deployment

### 1. Deploy to Google Cloud Functions

#### a. Zip the Application

```bash
zip -r function.zip .
```

#### b. Deploy via Google Cloud Console or CLI

**Using gcloud CLI:**

```bash
gcloud functions deploy slack_events_fn \
  --runtime python312 \
  --trigger-http \
  --allow-unauthenticated \
  --entry-point slack_events_fn \
  --memory 512MB \
```

**Parameters:**

- **--runtime**: Python version.
- **--trigger-http**: Expose the function via HTTP.
- **--allow-unauthenticated**: Allow public access.
- **--entry-point**: The function to execute (`slack_events_fn`).
- **--memory**: Allocate enough memory (recommended 512MB or higher).

#### c. Note the Function URL

After deployment, note the URL provided. This will be used in Slack app configuration.

## Slack App Setup

### 1. Create a Slack App

- Navigate to [Slack API](https://api.slack.com/apps) and click **"Create New App"**.
- Choose **"From scratch"** and provide an app name and select your workspace.

### 2. Configure OAuth & Permissions

- In your app settings, go to **OAuth & Permissions**.
- Under **Scopes**, add the following **Bot Token Scopes**:
  - `app_mentions:read`
  - `channels:history`
  - `reactions:read`
  - `chat:write`
  - `groups:history`
  - `reactions:read`
  - `reactions:write`
  - `users:read`
  - `im:history`

### 3. Configure Event Subscriptions

- Go to **Event Subscriptions** and toggle **Enable Events** to **On**.
- **Request URL**: Enter your Google Cloud Function URL.
- Under **Subscribe to Bot Events**, add:
  - `message.channels`
  - `reaction_added`

### 4. Configure Interactivity & Shortcuts

- Go to **Interactivity & Shortcuts** and toggle **Interactivity** to **On**.
- **Request URL**: Enter your Google Cloud Function URL.

### 5. Install the App to Your Workspace

- Go to **Install App** and click **"Install App to Workspace"**.
- Authorize the app to your workspace.
- Copy the **Bot User OAuth Token** and **Signing Secret** to your `.env` file or set them as environment variables in Google Cloud.

## License

This project is licensed under the [MIT License](LICENSE).

## Acknowledgments

- [Slack API](https://api.slack.com/)
- [Google Cloud Functions](https://cloud.google.com/functions)
- [Vertex AI](https://cloud.google.com/vertex-ai)
- [Slack Bolt for Python](https://slack.dev/bolt-python/)
