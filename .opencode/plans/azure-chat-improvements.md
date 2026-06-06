# Plan: Azure Config + Interactive Chat Mode

## 1. Azure OpenAI — Proper `azure_deployment` + `api_version` config

### File: `src/ctxgraph/config/settings.py`

#### 1a. Default config — add azure fields
Add to `DEFAULT_CONFIG["ai"]`:
```python
"azure_deployment": None,
"api_version": "2024-08-01-preview",
```

#### 1b. Env overrides — add to `_apply_env_overrides()`
```python
env_azure_deploy = os.environ.get("AZURE_OPENAI_DEPLOYMENT")
if env_azure_deploy:
    self._data["ai"]["azure_deployment"] = env_azure_deploy

env_api_version = os.environ.get("AZURE_OPENAI_API_VERSION")
if env_api_version:
    self._data["ai"]["api_version"] = env_api_version
```

#### 1c. New properties on `Settings` class
```python
@property
def azure_deployment(self) -> str:
    dep = self._data["ai"].get("azure_deployment")
    return dep if dep else self.model

@property
def api_version(self) -> str:
    return self._data["ai"].get("api_version", "2024-08-01-preview")
```

#### 1d. Update `get_chat_url()` — use configurable api_version
Replace hardcoded `api-version=2024-08-01-preview` in the Azure `chat_endpoint` with a dynamic value:
- Change `PROVIDER_CONFIGS["azure"]["chat_endpoint"]` to:
  `/openai/deployments/{deployment}/chat/completions?api-version={api_version}`
- In `get_chat_url()`, replace `{api_version}` with `self.api_version` and `{deployment}` with `self.azure_deployment`

#### 1e. Update `create_default_config()` — add commented Azure fields
Add to the default config.toml template:
```toml
# For Azure provider, uncomment and set:
# azure_deployment = "my-gpt-4o-deployment"
# api_version = "2024-08-01-preview"
#   endpoint = "https://YOUR-RESOURCE.openai.azure.com"
```

### File: `src/ctxgraph/cli/main.py`

#### 1f. In `ask` command — use azure_deployment for model in request body
When building the LLM request body, use `settings.azure_deployment` instead of `settings.model` if provider is azure (otherwise model name may not match the deployment name).

Same change needed in the `chat` command.

---

## 2. Interactive Chat REPL Mode

### File: `src/ctxgraph/chat.py` — new functions

#### 2a. `delete_session(repo_path, session_id)`
Remove the session JSONL file.

#### 2b. `interactive_session_picker(repo_path) -> str | None`
- List sessions via `list_sessions()`
- If no sessions, return `None` (creates new session)
- Use Rich `Live` display + cross-platform keyboard input for arrow-key navigation
- Windows: `msvcrt.getch()` for arrow keys
- Unix: `tty.setraw()` + `sys.stdin.read()`
- User presses ↑/↓ to highlight row, Enter to select
- Returns `session_id` string

### File: `src/ctxgraph/cli/main.py` — refactor `chat()` command

#### 2c. New helper: `_show_chat_help()`
Print available slash commands.

#### 2d. New helper: `_send_chat_message(path, session_id, message, settings) -> str`
Extract the LLM call logic from current chat() into a reusable function that:
- Creates session if `session_id` is None
- Checks token limit, auto-compacts if needed
- Loads session history, builds capsule, calls LLM
- Appends user message + assistant response to session
- Prints response + savings table + token count
- Returns the new/continued `session_id`

#### 2e. Refactor `chat()` function

**When `message` is provided:**
- Create session or get active
- Call `_send_chat_message()`
- Enter REPL loop (stay in chat mode)

**When `message` is NOT provided:**
- Print "Chat mode. Type /help for commands."
- Enter REPL loop immediately
- No session created until first message

**REPL loop logic:**
```python
session_id = None
while True:
    try:
        user_input = console.input("[bold cyan]>[/bold cyan] ")
    except (KeyboardInterrupt, EOFError):
        console.print("\n[yellow]Exiting chat.[/yellow]")
        break

    if not user_input.strip():
        continue

    if user_input.startswith("/"):
        cmd = user_input[1:].strip().lower().split()[0]
        if cmd == "exit":
            break
        elif cmd == "help":
            _show_chat_help()
        elif cmd == "list":
            _show_sessions(path)
        elif cmd == "resume":
            sid = interactive_session_picker(path)
            if sid:
                session_id = sid
                console.print(f"[green]Resumed session {sid}[/green]")
        elif cmd == "show":
            if session_id:
                context = show_session_context(path, session_id)
                console.print(context)
            else:
                console.print("[yellow]No active session.[/yellow]")
        elif cmd == "compact":
            if session_id:
                compact_session(path, session_id)
                console.print("[green]Session compacted.[/green]")
            else:
                console.print("[yellow]No active session.[/yellow]")
        elif cmd == "new":
            session_id = create_session(path)
            console.print(f"[green]Started new session {session_id}[/green]")
    else:
        session_id = _send_chat_message(path, session_id, user_input, settings)
```

#### 2f. Single-shot `ctx chat "message"` also enters REPL
After sending the message and showing response, the REPL loop continues.

---

## 3. README Updates

- Azure section: show full config with `azure_deployment`, `api_version`, endpoint
- Azure env vars: `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_API_VERSION`
- Interactive chat: document REPL mode, all slash commands, /resume picker
- Update environment variables table

---

## 4. E2E Tests

### File: `tests/test_e2e.py` — new classes

#### `TestE2EChat`
| Test | Description |
|------|-------------|
| `test_create_session` | Creates session, verifies dir + valid UUID |
| `test_append_read_messages` | Writes user/assistant, reads back |
| `test_list_sessions` | Creates 2 sessions, lists, checks counts |
| `test_compact_session` | Adds 5 messages, compacts, verifies summary |
| `test_get_active_session` | Creates 2, checks most recent returned |
| `test_delete_session` | Creates then deletes, verifies gone |
| `test_session_token_count` | Verifies rough token counting |

#### Azure config tests (add to existing `TestSettings`)
| Test | Description |
|------|-------------|
| `test_azure_deployment_property` | Check `azure_deployment` falls back to `model` |
| `test_azure_deployment_explicit` | Set `azure_deployment`, verify it's used |
| `test_azure_api_version_default` | Default is `"2024-08-01-preview"` |
| `test_azure_api_version_config` | Load config with custom api_version |
| `test_azure_env_deployment` | `AZURE_OPENAI_DEPLOYMENT` env var |
| `test_azure_env_api_version` | `AZURE_OPENAI_API_VERSION` env var |

---

## 5. Package data

`pyproject.toml` already updated with `[tool.setuptools.package-data]` for `.toml` files (done in previous session).
