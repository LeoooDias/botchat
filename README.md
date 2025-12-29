# botchat

A privacy-first AI chat application with multi-bot support. Chat with multiple AI models simultaneously (OpenAI, Gemini, Claude) with full control over your data.

## ✨ Features

- **Multi-Bot Chat** - Run multiple AI models in parallel in a single conversation
- **Privacy-First** - Your conversations are never stored on servers or used for training
- **Real-Time Streaming** - See responses as they're generated
- **File Attachments** - Upload PDFs, images, and text files for AI analysis
- **Bot Library** - Save and organize bot configurations with categories
- **BYOK Support** - Bring your own API keys for unlimited usage
- **Response Modifiers** - Toggle between Chat (brief) and Deep (comprehensive) response modes

## 🔑 Supported AI Providers

| Provider | Models | Privacy |
|----------|--------|---------|
| Anthropic | Claude Sonnet 4.5, Claude Haiku 4.5, Claude Opus 4.5 | Not used for training |
| Google Gemini | Gemini 3 Pro Preview, Gemini 3 Flash Preview, Gemini 2.5 Flash, Gemini 2.5 Flash Lite, Gemini 2.5 Pro | Paid API tier (no training) |
| OpenAI | GPT-5.2, GPT-5, GPT-5 Nano, GPT-4.1, GPT-5 Mini | Not used for training |

## 🛠️ Self-Hosting

### Prerequisites

- Docker and Docker Compose
- PostgreSQL database
- API keys from at least one AI provider (OpenAI, Google, or Anthropic)
- OAuth credentials (GitHub and/or Google) for authentication

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/YourUsername/botchat.git
   cd botchat
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start with Docker Compose**
   ```bash
   docker-compose up -d
   ```

4. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000

### Environment Variables

See `.env.example` for all required configuration options:

- `DATABASE_URL` - PostgreSQL connection string
- `JWT_SECRET` - Secret key for JWT token signing
- `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET` - GitHub OAuth (optional)
- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` - Google OAuth (optional)
- Platform API keys for hosted usage (optional)

### Manual Setup (Without Docker)

**Backend (Python 3.11+)**
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Frontend (Node.js 20+)**
```bash
cd frontend
npm install
npm run build
npm run preview
```

## 📁 Project Structure

```
botchat/
├── backend/           # FastAPI Python backend
│   ├── app/
│   │   ├── main.py    # API routes and SSE streaming
│   │   ├── auth.py    # OAuth authentication
│   │   ├── database.py
│   │   └── ...
│   └── Dockerfile
├── frontend/          # SvelteKit frontend
│   ├── src/
│   │   ├── routes/    # Pages
│   │   └── lib/       # Components and stores
│   └── Dockerfile
├── docker-compose.yml
└── .env.example
```

## 🔒 Privacy Architecture

- **No server-side conversation storage** - Messages exist only in your browser's localStorage
- **Client-side encryption** - API keys are encrypted with AES-256 before storage
- **Zero retention providers** - All supported AI providers configured for zero data retention
- **Minimal auth data** - Only email/name stored for authentication

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.
