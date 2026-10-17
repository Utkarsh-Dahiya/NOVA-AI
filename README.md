NOVA AI --- Multi-Model AI Chatbot

NOVA AI is a Streamlit-based chatbot interface that lets users chat with
AI models from multiple providers through one application. It uses
LangChain integrations to connect supported model providers and provides
a custom dark-themed interface.

Features

Multi-provider interface: Choose between Groq, Google Gemini,
OpenAI, and Mistral.

Chat interface: Send prompts and view model responses in the
NOVA UI.

Provider configuration: Uses environment variables for API keys.

Streamlit application: Runs locally and can be deployed to
Streamlit Community Cloud.

Provider-specific errors: Credentials, model access, quotas, and
rate limits can affect individual providers.

Provider availability depends on valid API credentials, the selected
model, provider-side access, and usage limits. A provider appearing in
the selector does not guarantee that its API is available.

Technology Stack

Python

Streamlit

LangChain

Groq, Google Gemini, OpenAI, and Mistral integrations

python-dotenv

Project Structure

The project may look similar to this:

Basic-AI-Chatbot/
├── app.py
├── requirements.txt
├── nova/
│   ├── providers.py
│   ├── chat_service.py
│   ├── state.py
│   └── ui/
│       ├── components.py
│       └── styles.css
└── .streamlit/
    └── config.toml

Your local project may include additional files. Keep local virtual
environments, caches, and secret files out of version control.

Requirements

A Python version compatible with the installed project dependencies

API key(s) for the provider(s) you want to use

Git and a GitHub account for deployment

A Streamlit Community Cloud account for hosting

Run Locally

1. Open the project directory

In PowerShell, navigate to the folder containing app.py:

cd "C:\path\to\Basic-AI-Chatbot"

2. Create and activate a virtual environment (if needed)

py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1

If PowerShell blocks activation, run this for the current terminal
session and activate again:

Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1

If you already have a working virtual environment, you can keep using
it.

3. Install dependencies

python -m pip install -r requirements.txt

4. Configure API keys

Create a .env file in the location expected by nova/providers.py.
Example:

GROQ_API_KEY=replace_with_your_groq_key
GOOGLE_API_KEY=replace_with_your_google_key
OPENAI_API_KEY=replace_with_your_openai_key
MISTRAL_API_KEY=replace_with_your_mistral_key

Only add keys for providers you intend to use. Replace example values
with your own credentials. Never commit real API keys to GitHub or share
them in screenshots, logs, or messages.

5. Start NOVA AI

Run this from the directory containing app.py:

python -m streamlit run app.py

Streamlit will print a local address in the terminal, usually
http://localhost:8501.

Deploy to Streamlit Community Cloud

Ensure the app runs locally and requirements.txt lists the
required external packages.

Push the project to a GitHub repository.

Confirm that .env, .venv/, Python cache files, and
.streamlit/secrets.toml are excluded by .gitignore.

Open Streamlit Community Cloud and
create an app from the repository.

Set the app's main file path to app.py (relative to the repository
root).

Add provider credentials under the app's Settings → Secrets.

Confirm the provider code can read deployed secrets. Streamlit
secrets are available through st.secrets; they are not
automatically loaded from a local .env file. If the app reads only
environment variables, configure a safe bridge or update provider
configuration to support Streamlit secrets.

Deploy and test each provider separately.

Example Streamlit secrets format:

GROQ_API_KEY = "your_groq_key"
GOOGLE_API_KEY = "your_google_key"
OPENAI_API_KEY = "your_openai_key"
MISTRAL_API_KEY = "your_mistral_key"

Use only the keys you need. Do not put real credentials in this README
or in the Git repository.

Troubleshooting

A provider says its API key is missing

Verify that the key name matches the one expected by
nova/providers.py.

Verify that the .env file is in the location the code loads.

Restart Streamlit after changing local environment configuration.

On Streamlit Community Cloud, add keys in app Secrets and ensure the
application reads them.

A provider returns an authentication error

Check that the key is valid, active, and belongs to the correct
provider. Never paste the key into public issue reports.

A provider returns a quota or rate-limit error

Check the provider's usage dashboard and limits. A quota or rate-limit
response is different from a missing-key error.

Streamlit says app.py cannot be found

Run Get-Location and Get-ChildItem in PowerShell. Change directory
to the folder that contains app.py, then run the Streamlit command
again.

A Python package is missing

Activate the project's virtual environment and run:

python -m pip install -r requirements.txt

Security

Never commit .env, .streamlit/secrets.toml, or API credentials.

Keep .venv/, __pycache__/, and compiled Python files out of Git.

Rotate any API key that was accidentally exposed.

Use provider keys only in trusted local configuration or the hosting
platform's secret manager.

Future Improvements

Potential next steps include persistent conversation history,
conversation renaming and deletion, response streaming, retry controls,
exportable conversations, configurable generation settings, and
additional automated tests.

License

No license has been specified yet. Add a LICENSE file before
presenting the repository as open source, and choose a license
appropriate for your project.
