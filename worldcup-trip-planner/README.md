## 1 Pre-requisites Installation on Your Machine
# GCloud CLI
Install gcloud cli from https://cloud.google.com/sdk/docs/install
Follow these setup instructions: https://docs.cloud.google.com/sdk/docs/install-sdk

# Python 3.11+
python --version

# Node.js 20+
node --version

# Install Python packages
pip install google-adk pymongo python-dotenv flask

# Test MongoDB MCP server works
npx -y mongodb-mcp-server@latest --help

Verify your installations by running these commands in your terminal:
python --version
node --version
npm --version

## Step 2: Clone
# Clone the repository
git clone https://github.com/sanjana650/worldcup-trip-planner.git

# Move inside the project folder
cd worldcup-trip-planner


## Step 3: Set Up a Virtual Environment & Dependencies

# Create the Environment
Windows (PowerShell):
python -m venv .venv
.venv\Scripts\Activate.ps1

macOS / Linux (Bash):
python3 -m venv .venv
source .venv/bin/activate

# Install Project Requirements
Once your terminal shows (.venv) at the beginning of the prompt line, install all our core packages at once:

Bash
pip install -r requirements.txt

## Step 4: Local Configuration (.env)
(Check group for env requirements)

## Step 5: Verify Your Setup Works

# 1. Test the MongoDB Atlas connection
python -c "from pymongo import MongoClient; import os; from dotenv import load_dotenv; load_dotenv(); client = MongoClient(os.getenv('MONGODB_URI')); print('Databases:', client.list_database_names()); print('🎉 MongoDB Atlas Connected Successfully!')"

# 2. Test the Gemini AI API connection
python -c "import google.generativeai as genai; import os; from dotenv import load_dotenv; load_dotenv(); genai.configure(api_key=os.getenv('GOOGLE_API_KEY')); model = genai.GenerativeModel('gemini-2.5-flash'); print('Gemini Response:', model.generate_content('Say hello!').text)"