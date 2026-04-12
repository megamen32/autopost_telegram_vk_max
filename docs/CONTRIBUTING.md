# Contributing Guide

Thank you for your interest in contributing to AutoPost Sync! This guide will help you get started.

## Code of Conduct

Be respectful, inclusive, and constructive in all interactions.

## Getting Started

### 1. Fork & Clone

```bash
# Fork the repository on GitHub

# Clone your fork
git clone https://github.com/yourusername/autopost_sync.git
cd autopost_sync

# Add upstream remote
git remote add upstream https://github.com/original/autopost_sync.git
```

### 2. Create Development Branch

```bash
# Sync with latest upstream
git fetch upstream
git checkout upstream/main

# Create feature branch
git checkout -b feature/my-feature
# or
git checkout -b fix/my-bug-fix
```

### 3. Set Up Development Environment

```bash
# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Install with dev dependencies
pip install -e ".[dev,vk-browser]"

# Install pre-commit hooks (optional but recommended)
pip install pre-commit
pre-commit install
```

### 4. Make Your Changes

Keep commits focused and logical. See **Commit Guidelines** below.

### 5. Test Your Changes

```bash
# Run unit tests
pytest tests/unit/ -v

# Run specific test file
pytest tests/unit/test_vk_adapter.py -v

# Run with coverage
pytest --cov=app tests/

# Format code
black .
isort .

# Check style
flake8 app/
mypy app/
```

### 6. Push & Create PR

```bash
git push origin feature/my-feature
```

Visit GitHub and create a Pull Request. Fill in the PR template.

## Project Structure

```
autopost_sync/
├── app/
│   ├── adapters/          # Platform adapters (Telegram, VK, MAX)
│   │   ├── base.py        # BaseAdapter abstract class
│   │   ├── definitions.py  # Adapter definitions & factories
│   │   ├── schema.py       # Configuration schema
│   │   ├── telegram/
│   │   ├── vk/
│   │   └── max/
│   ├── api/               # FastAPI endpoints
│   ├── db/                # SQLAlchemy models
│   ├── domain/            # Domain models (UnifiedPost, enums)
│   ├── repositories/      # Data access layer
│   ├── services/          # Business logic
│   ├── workers/           # Background workers
│   ├── utils/             # Utilities (crypto, etc.)
│   └── main.py            # FastAPI app entry
├── docs/                  # Documentation
├── tests/                 # Unit & integration tests
├── alembic/               # Database migrations
├── pyproject.toml         # Dependencies & metadata
├── README.md              # Project overview
└── docker-compose.yml     # Local development database
```

## Adding a New Adapter

### 1. Create Adapter Structure

```bash
mkdir -p app/adapters/myplatform
touch app/adapters/myplatform/__init__.py
touch app/adapters/myplatform/adapter.py
touch app/adapters/myplatform/client.py
touch app/adapters/myplatform/README.md
```

### 2. Implement BaseAdapter

```python
# app/adapters/myplatform/adapter.py
from app.adapters.base import BaseAdapter
from app.domain.enums import Platform
from app.domain.models import UnifiedPost

class MyPlatformAdapter(BaseAdapter):
    platform = Platform.MYPLATFORM  # Add to Platform enum first
    
    def __init__(self, *, instance_id: str | None = None, **kwargs):
        super().__init__(instance_id=instance_id)
        # Store adapter-specific params
    
    @property
    def enabled(self) -> bool:
        # Return True if adapter is properly configured
        return bool(self.token)
    
    async def startup(self, on_post=None) -> None:
        # Initialize connection, start listening, etc.
        self._on_post = on_post
        # ... your startup logic
    
    async def shutdown(self) -> None:
        # Clean up connections
        pass
    
    async def parse_incoming_event(self, payload: dict) -> UnifiedPost | None:
        # Convert platform event to UnifiedPost
        return UnifiedPost(
            source_platform=self.platform,
            source_adapter_id=self.instance_id,
            source_chat_id=str(payload.get("chat_id")),
            source_message_id=str(payload.get("message_id")),
            text=payload.get("text"),
            media=[],
        )
    
    async def publish_post(self, chat_id: str, post: UnifiedPost) -> str:
        # Publish to platform, return post ID
        return "post_id"
```

### 3. Create Definition

```python
# app/adapters/definitions.py (add to file)
from app.adapters.myplatform.adapter import MyPlatformAdapter

MYPLATFORM_DEFINITION = AdapterDefinition(
    adapter_key="myplatform",
    platform=Platform.MYPLATFORM.value,
    title="My Platform",
    description="Integration with My Platform",
    fields=[
        AdapterSettingField("display_name", "Название", "str", "simple", True, False, "..."),
        AdapterSettingField("token", "Token", "str", "simple", True, True, "..."),
        # ... more fields
    ],
    factory=lambda instance_id, config, secrets: MyPlatformAdapter(
        instance_id=instance_id,
        token=secrets.get("token"),
    ),
)
```

### 4. Register Adapter

```python
# app/adapters/definitions.py
class AdapterDefinitionRegistry:
    def __init__(self):
        self._defs = {
            # ... existing
            MYPLATFORM_DEFINITION.adapter_key: MYPLATFORM_DEFINITION,
        }
```

### 5. Write Tests

```python
# tests/unit/test_myplatform_adapter.py
import pytest
from app.adapters.myplatform.adapter import MyPlatformAdapter
from app.domain.models import UnifiedPost

def test_adapter_enabled():
    adapter = MyPlatformAdapter(instance_id="test", token="token")
    assert adapter.enabled

def test_parse_incoming_event():
    adapter = MyPlatformAdapter(instance_id="test", token="token")
    payload = {"chat_id": "123", "message_id": "456", "text": "Hello"}
    post = adapter.parse_incoming_event(payload)
    assert post.text == "Hello"
    assert post.source_chat_id == "123"

@pytest.mark.asyncio
async def test_publish_post():
    adapter = MyPlatformAdapter(instance_id="test", token="token")
    post = UnifiedPost(...)
    result = await adapter.publish_post("chat_123", post)
    assert result  # Should return post ID
```

### 6. Document Adapter

Create `app/adapters/myplatform/README.md` with:
- Features overview
- Setup instructions
- Configuration options
- Publishing examples
- Troubleshooting

### 7. Create PR

Push your branch and create a PR. Include:
- What the adapter does
- Setup instructions
- Test results
- Any limitations or known issues

## Commit Guidelines

### Format

```
<type>: <subject>

<body>

<footer>
```

### Types

- `feat:` — New feature
- `fix:` — Bug fix
- `refactor:` — Code refactoring without changing behavior
- `test:` — Add/update tests
- `docs:` — Documentation
- `chore:` — Dependency updates, tooling

### Examples

```
feat: add VK photo upload support

- Implement photos.getWallUploadServer() workflow
- Add automatic token refresh before media operations
- Handle multi-photo posts with attachments

Fixes #123
```

```
fix: handle 429 rate limit errors with exponential backoff

Previously, 429 errors were retried with constant delay.
Now using exponential backoff with jitter.

Fixes #456
```

## Code Style

### Black & isort

```bash
# Auto-format
black .
isort .

# Check without modifying
black --check .
isort --check-only .
```

### Type Hints

Use type hints for public APIs:

```python
async def publish_post(self, chat_id: str, post: UnifiedPost) -> str:
    """Publish a post to a chat. Returns the post ID."""
    pass
```

### Docstrings

```python
def some_function(arg: str) -> bool:
    """
    One-line summary.
    
    Longer description if needed. Explain why, not what.
    
    Args:
        arg: Description of arg
    
    Returns:
        Description of return value
    
    Raises:
        ValueError: When this happens
    """
    pass
```

### Logging

```python
import logging

logger = logging.getLogger(__name__)

logger.info("Adapter %s started", self.instance_id)
logger.error("Failed to publish: %s", exc, exc_info=True)
```

## Testing

### Unit Tests

Test isolated functions and classes:

```python
def test_sync_rule_applies_text_template():
    rule = SyncRule(copy_text_template="{text}\n#tag")
    result = rule.apply_text("Hello")
    assert result == "Hello\n#tag"
```

### Integration Tests

Test with real database/API (when needed):

```python
@pytest.mark.integration
async def test_publish_to_vk():
    # Requires VK_TEST_TOKEN env var
    adapter = VkAdapter(instance_id="test", token=os.getenv("VK_TEST_TOKEN"))
    post = UnifiedPost(...)
    post_id = await adapter.publish_post("123", post)
    assert post_id
```

Mark with `@pytest.mark.integration` to skip in CI unless explicitly enabled.

### Fixtures

```python
# tests/conftest.py
@pytest.fixture
async def db_session():
    """In-memory SQLite test database."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = sessionmaker(engine, class_=AsyncSession)
    async with async_session() as session:
        yield session
    
    await engine.dispose()
```

## Documentation

### When to Update Docs

- Adding a new feature → Update README
- Changing API → Update docs/API.md
- New adapter → Create app/adapters/name/README.md
- Installation steps changed → Update docs/INSTALLATION.md

### Writing Style

- Clear, concise, professional tone
- Use examples liberally
- Explain why, not just how
- Link to related docs

## Performance Considerations

### Async/Await

Use `async` for:
- Database queries
- HTTP requests
- File I/O

Don't use for:
- CPU-bound computations
- Simple data transformations

### Database

- Use indexes for frequently queried columns
- Batch operations when possible
- Prefer async queries (asyncpg, SQLAlchemy async)

### Media Handling

- Download to temp files, not memory
- Clean up after upload
- Respect platform file size limits

## Security

### Secrets

Never:
- Log secrets (tokens, passwords)
- Store in version control
- Pass in URLs or query params

Always:
- Encrypt at rest (SecretBox)
- Use environment variables
- Validate inputs at boundaries

### SQL Injection

Use:
- SQLAlchemy ORM (parameterized queries)
- Not raw SQL strings

### XSS

HTML templating is not in scope yet, but:
- Never trust user input
- Sanitize before display
- Use `markupsafe.escape()` if rendering HTML

## Reporting Issues

### Bug Reports

Include:
- Steps to reproduce
- Expected behavior
- Actual behavior
- Environment (OS, Python version, etc.)
- Relevant logs/tracebacks

### Feature Requests

Include:
- Use case / motivation
- Proposed solution
- Alternatives considered

## Getting Help

- **Discussions** — Ask questions, discuss features
- **Issues** — Report bugs, request features
- **Docs** — Check existing documentation
- **Code** — Read source code comments

## Release Process

Maintainers:

```bash
# Bump version in pyproject.toml
# Add to CHANGELOG.md
git commit -m "Release v0.3.0"
git tag -a v0.3.0 -m "Version 0.3.0"
git push origin main v0.3.0

# GitHub Actions auto-publishes to PyPI
```

## License

By contributing, you agree your code will be licensed under MIT (same as project).

## Thank You!

We appreciate your contributions and look forward to working together. 🙏
