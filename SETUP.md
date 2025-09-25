# Zivo Jewelry Chatbot Setup Guide

## Required Environment Variables

Create a `.env` file in the root directory with the following variables:

```env
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o

# Azure Dynamic Sessions (Required for Excel processing)
AZURE_POOL_MANAGEMENT_ENDPOINT=your_azure_pool_management_endpoint_here

# Database Configuration (SQL Server 2022 Express)
db_uri=mssql+pyodbc://localhost/YourDatabaseName?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes

# Alternative SQL Server connection with username/password:
# db_uri=mssql+pyodbc://username:password@localhost\\SQLEXPRESS/YourDatabaseName?driver=ODBC+Driver+17+for+SQL+Server

# Frontend Configuration (optional)
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Quick Start

### Option 1: Use the Development Script (Recommended)
```bash
python dev-start.py
```

### Option 2: Manual Startup

1. **Terminal 1 - Backend:**
   ```bash
   In root directory
   python -m uvicorn src.api:app --host 127.0.0.1 --port 8000 --reload
   ```

2. **Terminal 2 - Frontend:**
   ```bash
   cd frontend
   npm install --legacy-peer-deps
   npm run dev
   ```

## Access Points

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Health Check**: http://localhost:8000/health

## Troubleshooting

### PowerShell Commands
If using Windows PowerShell, commands must be run separately (no `&&` operator):
```powershell
cd frontend
npm run dev
```

### Dependencies
- Frontend: Run `npm install --legacy-peer-deps` if you encounter dependency conflicts
- Backend: Ensure all Python dependencies are installed via `pip install -r requirements.txt` or `uv sync`

### Database Connection
The chatbot requires a SQL Server 2022 Express database connection. Ensure your database is running and accessible with the connection string in your `.env` file.

### Excel Processing Setup
The spreadsheet analysis feature requires Azure Dynamic Sessions:
1. Set up an Azure Dynamic Sessions pool in your Azure account
2. Add the `AZURE_POOL_MANAGEMENT_ENDPOINT` to your `.env` file
3. Without this configuration, Excel file processing will fail with "couldn't generate a response" errors

### Security Note
⚠️ **NEVER commit your `.env` file to version control!** It contains sensitive API keys and credentials. 
