# Documentation Index

Complete documentation for AutoPost Sync. Start here to find what you need.

## 📖 Getting Started

**New to AutoPost Sync?** Start here:

1. **[Main README](../README.md)** — Project overview, features, quick start
2. **[Installation Guide](./INSTALLATION.md)** — Step-by-step setup for local development, Docker, or production
3. **[Architecture Overview](./ARCHITECTURE.md)** — Understand how the system works

## 🚀 Setup & Configuration

### Installation

- [**Installation Guide**](./INSTALLATION.md) — Complete setup instructions
  - Local development with venv
  - Docker Compose deployment
  - Production deployment with systemd + Nginx
  - Database configuration
  - Troubleshooting common issues

### Platform Adapters

Choose your platforms:

- [**Telegram Adapter**](../app/adapters/telegram/README.md)
  - Telethon client setup
  - Bot vs user mode
  - Real-time message receiving
  - Publishing text, photos, videos, documents

- [**VK Adapter**](../app/adapters/vk/README.md)
  - VK ID OAuth 2.0 setup
  - Community tokens and webhooks
  - Photo & video upload pipeline
  - Automatic token refresh
  - Browser fallback for local development

- [**MAX Adapter**](../app/adapters/max/README.md)
  - Long polling vs webhooks
  - Message sending and receiving
  - Media file handling
  - Official SDK vs HTTP API

## 💻 Development & API

### API Reference

- [**API Reference**](./API.md) — Complete REST API endpoints
  - Adapter instances management
  - Sync rules and routes
  - Delivery job monitoring
  - Authentication endpoints
  - Debug endpoints
  - Example curl commands

### System Architecture

- [**Architecture Overview**](./ARCHITECTURE.md) — Deep technical dive
  - Message flow (Telegram → VK example)
  - Core layers: domain, adapters, repositories, services, workers
  - Database schema and models
  - Encryption strategy
  - Error handling & retry logic
  - Scalability considerations
  - Security best practices

### Contributing

- [**Contributing Guide**](./CONTRIBUTING.md)
  - How to contribute
  - Code style and testing standards
  - Adding a new adapter (walkthrough)
  - Commit guidelines
  - PR process
  - Development environment setup

## 📚 Reference

### Concepts

**UnifiedPost** — Normalized message format used internally
- Text and media
- Metadata (source, destination, IDs)
- Message tracing for anti-loop detection

**Adapter Instance** — Pluggable platform configuration
- Configuration (stored in database)
- Secrets (encrypted at rest)
- Multiple instances of same platform supported

**Sync Rule** — Transform messages between platforms
- Source/target platform pair
- Content filtering (what media types to allow)
- Text template for copying messages

**Route** — Connect specific chats between adapters
- Source chat in source adapter
- Target chat in target adapter
- Routes are the concrete connections

**Delivery Job** — Async job for sending a message
- Queued when message needs to be sent
- Retried with exponential backoff on failure
- Tracked for monitoring and debugging

### Common Tasks

**Setting up your first adapter:**
1. Open http://localhost:8000/docs (interactive API)
2. Create adapter instance via `/api/adapter-instances` POST
3. Configure platform-specific settings
4. Test with `/webhooks/{adapter_instance_id}` POST

**Creating a sync rule:**
1. Define source and target platforms
2. Set content policy (which media types to allow)
3. Optional: provide text template for copying

**Creating a route:**
1. Choose source adapter instance and chat ID
2. Choose target adapter instance and chat ID
3. Enable the route
4. Messages will now flow from source to target

**Monitoring message delivery:**
1. Check `/api/delivery-jobs` for queue status
2. View individual jobs with `/api/delivery-jobs/{job_id}`
3. Retry failed jobs with `/api/delivery-jobs/{job_id}/retry`

## 🔧 Operations

### Deployment

- [**Installation Guide**](./INSTALLATION.md) — Including production deployment section
  - Systemd service configuration
  - Nginx reverse proxy setup
  - SSL/TLS with Let's Encrypt
  - Database backups
  - Monitoring logs

### Troubleshooting

- [**Installation Guide - Troubleshooting**](./INSTALLATION.md#troubleshooting)
- [**Telegram Adapter - Troubleshooting**](../app/adapters/telegram/README.md#troubleshooting)
- [**VK Adapter - Troubleshooting**](../app/adapters/vk/README.md#troubleshooting)
- [**MAX Adapter - Troubleshooting**](../app/adapters/max/README.md#troubleshooting)

### Monitoring

- Use `/api/debug/delivery-jobs` to check queue status
- Use `/api/debug/adapter-logs` to view adapter-specific logs
- Use `/api/debug/db-status` to check database connectivity
- Enable `log_level: DEBUG` in adapter config for more verbosity

## 🎓 Learning Path

**Beginner:**
1. Read [Main README](../README.md)
2. Follow [Installation Guide](./INSTALLATION.md) to set up locally
3. Set up one adapter (e.g., Telegram) following [Telegram Adapter README](../app/adapters/telegram/README.md)

**Intermediate:**
1. Read [Architecture Overview](./ARCHITECTURE.md) to understand the system
2. Create sync rules and routes via API
3. Monitor delivery via debug endpoints

**Advanced:**
1. Read [Contributing Guide](./CONTRIBUTING.md)
2. Explore source code in `app/adapters`, `app/services`, `app/workers`
3. Write custom adapter by extending `BaseAdapter`
4. Run tests: `pytest tests/ -v`

## 🤝 FAQ

### General

**Q: What's the difference between an adapter and an adapter instance?**
A: An adapter is a platform type (Telegram, VK, MAX). An adapter instance is a specific configuration of that adapter (e.g., "telegram-main", "telegram-backup"). You can have multiple instances of the same adapter.

**Q: Can I use this with multiple databases?**
A: Currently, only one PostgreSQL database is supported. SQLite can be used for local development.

**Q: Is there a web UI?**
A: Interactive API at http://localhost:8000/docs. A graphical web UI is planned for future releases.

### Telegram

**Q: What's the difference between bot mode and user mode?**
A: Bot mode requires a bot token from BotFather. User mode requires your Telegram account credentials. User mode has more access but requires authentication. Bot mode is simpler for public channels.

**Q: Can I use the same bot token for multiple instances?**
A: Yes, but each instance will have its own configuration. Only create multiple instances if they have different settings.

### VK

**Q: What's VK ID vs classic VK OAuth?**
A: VK ID is for user authentication. Classic VK OAuth is the older flow. For publishing photos/videos, use VK ID. For webhook events, use the classic app token.

**Q: Why am I getting "Method is unavailable"?**
A: You're using a VK ID token that doesn't support classic API methods. Use the proper VK OAuth flow to get an API token.

**Q: What's the browser fallback?**
A: Optional local automation using Chrome. Use only for development. Production should use official VK API.

### MAX

**Q: Long polling or webhooks?**
A: Long polling is easier for local development (no HTTPS needed). Webhooks are better for production but require public HTTPS endpoint.

**Q: Can I subscribe to custom event types?**
A: Yes, set `update_types` in adapter config. Check MAX docs for available types.

## 📞 Support

- **Issues** — Report bugs on GitHub
- **Discussions** — Ask questions and discuss features
- **Docs** — Check this documentation
- **Code Comments** — Read inline code documentation

## 📄 License

This project is licensed under MIT License.
See [LICENSE](../LICENSE) for details.

## 🗺️ Document Map

```
AutoPost Sync Project/
├── README.md                          ← Project overview (start here)
├── docs/
│   ├── README.md                      ← This file
│   ├── INSTALLATION.md                ← Setup guide
│   ├── ARCHITECTURE.md                ← System design deep dive
│   ├── API.md                         ← API reference
│   └── CONTRIBUTING.md                ← Development guidelines
├── app/adapters/
│   ├── telegram/
│   │   └── README.md                  ← Telegram-specific setup
│   ├── vk/
│   │   └── README.md                  ← VK-specific setup
│   └── max/
│       └── README.md                  ← MAX-specific setup
└── [Source code...]
```

---

**Last Updated:** April 2026  
**Documentation Version:** 1.0
