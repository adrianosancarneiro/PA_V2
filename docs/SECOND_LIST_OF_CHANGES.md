# Second List of Changes — Item #3

## Compose New Email (Contacts, Provider Selection, LLM First-Draft)

### 0) Objective
Describe new feature enabling composing brand-new emails from Telegram with provider and contact selection, automatic LLM draft generation, and recording sent messages.

### 1) Scope
- Telegram Compose flow for provider, recipients, subject, body and approval.
- Local contacts lookup with ranking.
- Provider-agnostic send pipeline using adapters.
- Database support for outbound messages and draft revisions.

### 2) User Stories
- **US-CMP-01**: Start compose, choose provider, recipients, first draft auto generated.
- **US-CMP-02**: Search contacts and add To/CC/BCC.
- **US-CMP-03**: After sending, confirmation and view thread option.

### 3) Functional Requirements
- **FR-1**: Compose entry points via button and `/compose` command.
- **FR-2**: Recipient picking with search, manual email entry and CC/BCC.
- **FR-3**: Subject and body prompting with LLM first draft, approve/edit/regenerate.
- **FR-4**: Send semantics capturing provider ids and storing outbound info.
- **FR-5**: Contacts sourced from local messages with frequency ranking.

### 4) Non-Functional Requirements
- Minimal Telegram UX steps, email validation, provider retry/backoff and isolated adapters.

### 5) Data Model (PostgreSQL)
Includes `contacts` table and outbound fields (`direction`, recipient arrays) on `email_messages`.

### 6) Provider Adapters
- `gmail_send_message` – encode RFC-2822 message and send via Gmail API.
- `outlook_send_mail` – send via Microsoft Graph `/me/sendMail` endpoint.

### 7) Repository & Service Code
- `contacts_repo.search_contacts(q)` for ranked lookups.
- `email_repo.create_outbound_draft(...)` and `mark_outbound_sent(...)` for state.

### 8) Telegram Flow
State machine steps: provider → recipients → subject → draft (LLM) → approve/send.

### 9) Best Practices
Always draft first, validate emails, respect rate limits and privacy, and maintain logging and idempotency.

### 10) Acceptance Tests
Outlined tests cover compose basics, CC/BCC, search, draft editing, provider paths, validation and resilience.
