# Google Services

Set up Gmail, Google Calendar, Google Drive, and Google Sheets access for your agent.

## Prerequisites

- A Google Cloud project
- OAuth 2.0 credentials (Client ID + Client Secret)

## Step 1: Create Google Cloud Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select an existing one)
3. Enable the APIs you need:
    - Gmail API
    - Google Calendar API
    - Google Drive API
    - Google Sheets API
4. Go to **Credentials** → **Create Credentials** → **OAuth 2.0 Client ID**
5. Application type: **Desktop app**
6. Download the credentials

## Step 2: Configure Vandelay

Add your credentials to `~/.vandelay/.env`:

```bash
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_PROJECT_ID=your-project-id
```

## Step 3: Authenticate

```bash
vandelay auth-google
```

This opens a browser (or prints a URL for headless servers) for OAuth consent. The token is saved to `~/.vandelay/google_token.json`.

### Headless Servers

On servers without a browser, `auth-google` prints a URL. Open it on any device, complete the consent flow, and paste the authorization code back into the terminal.

## Step 4: Enable Google Tools

```bash
vandelay tools enable gmail googlecalendar googledrive googlesheets
```

## Available Google Tools

| Tool | Capabilities |
|------|-------------|
| `gmail` | Read, send, search emails. HTML body support. |
| `googlecalendar` | List, create, update, delete events |
| `googledrive` | List, search, read, upload files |
| `googlesheets` | Read, write, create spreadsheets |

## Configuration

Set your calendar ID in `config.json` (defaults to `"primary"`):

```json
{
  "google": {
    "calendar_id": "primary"
  }
}
```

## Token Refresh

The OAuth token auto-refreshes. If it expires or is revoked, re-run `vandelay auth-google`.
