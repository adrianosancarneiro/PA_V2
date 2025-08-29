# PA_V2 Architecture Summary

## Proper Layer Organization

### Core Services Layer (`src/services/`)
- `email/email_repo.py` - Database operations for emails
- `email/contacts_repo.py` - Database operations for contacts  
- `email/jobs/monitor.py` - Email monitoring and fetching logic
- `email/providers/` - Gmail/Outlook API integrations
- `webhooks/` - Gmail push notification handlers
- `repo/push_repo.py` - Push state management for webhooks

### Interface Layer (`src/interfaces/`)
- `telegram/views/commands.py` - Command handlers (/digest, /compose, /status)
- `telegram/views/handlers.py` - Callback handlers for inline buttons
- `telegram/views/compose_handlers.py` - Multi-step compose flow handlers
- `telegram/views/digest.py` - Email digest formatting

### Core Infrastructure (`src/core/`)
- `database.py` - Database connections
- `repositories/` - Repository interfaces

## Why Compose is in Interface Layer

The `compose_handlers.py` is correctly placed in `src/interfaces/telegram/views/` because:

1. **UI/UX Logic**: It handles Telegram-specific user interaction flows
2. **State Management**: Manages conversation state through Telegram's context
3. **Input Validation**: Processes user input from Telegram messages
4. **Presentation**: Formats messages and keyboards for Telegram UI
5. **Integration**: Orchestrates calls to multiple services (contacts, email sending, repo)

The actual **email sending logic** remains in:
- `src/providers/gmail_send.py` - Gmail API sending
- `src/providers/outlook_send.py` - Outlook Graph API sending

## Service vs Interface Separation

### Services (Business Logic)
- Email fetching, parsing, storage
- Contact management
- Database operations
- Provider API integrations

### Interfaces (User Interaction)
- Command parsing and routing
- User flow management
- Response formatting
- Platform-specific UI logic

This follows proper **separation of concerns** where:
- Services handle **what** to do
- Interfaces handle **how** users interact with it
