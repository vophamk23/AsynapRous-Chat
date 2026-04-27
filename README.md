# AsynapRous – Hybrid P2P Chat System

> **CO3093/CO3094 – Computer Networks | HCMC University of Technology (VNU-HCM)**
> Built entirely from scratch using Python standard library — no Flask, no Django.


## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Requirements](#requirements)
- [Quick Start](#quick-start)
- [System Ports](#system-ports)
- [Key URLs](#key-urls)
- [Features](#features)
- [API Reference](#api-reference)
- [CLI Commands](#cli-commands)
- [Account Management](#account-management)
- [Technical Design](#technical-design)


## Overview

**AsynapRous** is a hybrid Peer-to-Peer (P2P) chat application built on top of a custom HTTP framework of the same name. The system implements a **Hybrid P2P** architecture: a central **Tracker** server handles peer discovery and authentication, while actual messages are sent **directly between peers** without passing through any central server.

The entire networking stack — TCP socket server, HTTP parser, request/response builder, routing decorator, reverse proxy, and load balancer — is implemented using only Python's standard library (`socket`, `threading`, `asyncio`, `selectors`).

Two client modes are available:

- **Web UI** (`start_peer.py`) — browser-based chat interface with polling
- **CLI** (`start_peer_cli.py`) — terminal-based client with multi-channel and broadcast support


## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        HYBRID P2P SYSTEM                        │
│                                                                 │
│   ┌──────────────────────────────────────────────────────────┐  │
│   │              PHASE 1: Client-Server (Tracker)            │  │
│   │                                                          │  │
│   │   Browser ──── POST /login ────► Tracker :9000           │  │
│   │   Browser ──── POST /submit-info ─► peer_list{}          │  │
│   │   Browser ──── GET  /get-list  ──► {username: ip:port}   │  │
│   └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│   ┌──────────────────────────────────────────────────────────┐  │
│   │              PHASE 2: Peer-to-Peer (Direct)              │  │
│   │                                                          │  │
│   │   Peer A :9001 ──── POST /receive-message ──► Peer B :9002  │
│   │   Peer B :9002 ──── POST /receive-message ──► Peer A :9001  │
│   │               (no Tracker involved)                      │  │
│   └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│   ┌──────────────────────────────────────────────────────────┐  │
│   │              OPTIONAL: Reverse Proxy                     │  │
│   │                                                          │  │
│   │   Client ──► Proxy :8888 ──round-robin──► Backend pool   │  │
│   └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### AsynapRous Framework Stack

```
Application Layer  │  start_tracker.py / start_peer.py
                   │  @app.route() decorators
───────────────────┼──────────────────────────────────
Framework Layer    │  AsynapRous (asynaprous.py)
                   │  Router: {(METHOD, path) → handler}
───────────────────┼──────────────────────────────────
Adapter Layer      │  HttpAdapter (httpadapter.py)
                   │  Parse headers, body, cookies → dispatch
───────────────────┼──────────────────────────────────
Transport Layer    │  Backend (backend.py)
                   │  TCP socket + Threading / Asyncio / Selectors
```


## Project Structure

```
assign1-mmt/
├── daemon/                     # Core framework (AsynapRous)
│   ├── __init__.py
│   ├── asynaprous.py           # Web framework: routing decorator
│   ├── backend.py              # TCP server: threading / asyncio / selectors
│   ├── httpadapter.py          # HTTP parse + dispatch + cookie auth
│   ├── request.py              # Request object: method, path, headers, cookies
│   ├── response.py             # Response builder: 200/400/401/404/500
│   ├── proxy.py                # Reverse proxy + round-robin load balancing
│   └── dictionary.py           # CaseInsensitiveDict for HTTP headers
│
├── start_tracker.py            # Tracker server (login, peer registry, get-list)
├── start_peer.py               # Peer server – Web UI mode
├── start_peer_cli.py           # Peer client – CLI mode (broadcast, DM, channel)
├── start_proxy.py              # Reverse proxy server
├── start_backend.py            # Standalone backend demo
├── start_sampleapp.py          # AsynapRous framework demo app
├── manager.py                  # Shared state manager (multiprocessing)
│
├── www/                        # Static HTML pages
│   ├── login.html              # Login form
│   ├── index.html              # Home page (auth required)
│   ├── submit.html             # IP:Port registration form
│   ├── chat.html               # P2P chat window
│   ├── active-peers.html       # Peer list with Connect button
│   └── view-my-channels.html   # Connected channels view
│
├── static/
│   ├── js/
│   │   ├── chat.js             # Send/receive messages, 1s polling
│   │   └── active-peers.js     # Load peer list, connect handler
│   └── css/
│       └── styles.css
│
├── db/
│   ├── account.db              # SQLite user database
│   └── account.py              # User management CLI
│
├── config/
│   └── proxy.conf              # Proxy routing configuration (NGINX-like syntax)
│
├── tests/                      # Unit tests: BiMap, Manager, batch scripts
│
├── run_web.bat                 # One-click launch: 1 Proxy + 1 Tracker + 5 Peers (Web)
├── run_cli.bat                 # One-click launch: 2 Trackers + 5 Peers (CLI)
└── tracker.json                # Auto-generated: tracker IP:Port for peers to read
```


## Requirements

- **Python** 3.8+
- **No external packages required** — uses standard library only

```bash
# Verify Python version
python --version
```


## Quick Start

### Option 1 — One-click launch (Windows)

**Web UI mode** (recommended for demo):

```bash
run_web.bat
```

Launches 7 CMD windows automatically: 1 Tracker (port 9000) + 5 Peer servers (ports 9001–9005).

**CLI mode** (multi-channel broadcast demo):

```bash
run_cli.bat
```

Launches 7 CMD windows: 2 Trackers (ports 8001, 8002) + 5 CLI peer clients (ports 9001–9005).

### Option 2 — Manual launch

**Step 1 — Start Tracker:**

```bash
python start_tracker.py --server-ip 127.0.0.1 --server-port 9000
```

**Step 2 — Start Peer servers** (each in a separate terminal):

```bash
python start_peer.py --server-ip 127.0.0.1 --server-port 9001
python start_peer.py --server-ip 127.0.0.1 --server-port 9002
python start_peer.py --server-ip 127.0.0.1 --server-port 9003
```

**Step 3 — (Optional) Start Reverse Proxy:**

```bash
python start_proxy.py --server-ip 0.0.0.0 --server-port 8888
```

> Wait until each terminal shows `[Backend] Port XXXX is ready...` before proceeding.


### Step 4 — Register peers via browser

1. Open `http://127.0.0.1:9000/login` in a **private/incognito window** per user
2. Log in with credentials from the [accounts table](#account-management)
3. Submit your IP:Port on the `/submit-info` page (e.g., `127.0.0.1` : `9001`)
4. Navigate to `http://127.0.0.1:9001/active-peers` to see other online peers
5. Click **Connect** next to a peer, then open the chat window


## System Ports

| Service            | Port | Description                                  |
|--------------------|------|----------------------------------------------|
| Tracker Server     | 9000 | Central server: login, peer registry, get-list |
| Peer 1 (VoPham)    | 9001 | Peer HTTP server: chat, messages, active-peers |
| Peer 2 (MinhDuc)   | 9002 | Peer HTTP server                             |
| Peer 3 (TrungQuan) | 9003 | Peer HTTP server                             |
| Peer 4 (MinhKhang) | 9004 | Peer HTTP server                             |
| Peer 5 (ChanKien)  | 9005 | Peer HTTP server                             |
| Reverse Proxy      | 8888 | Load balancer (optional)                     |
| CLI Tracker 1      | 8001 | Tracker for CLI channel 1                    |
| CLI Tracker 2      | 8002 | Tracker for CLI channel 2                    |


## Key URLs

| URL | Description |
|-----|-------------|
| `http://127.0.0.1:9000/login` | Login page |
| `http://127.0.0.1:9000/index.html` | Home page (cookie `auth=true` required) |
| `http://127.0.0.1:9000/submit-info` | Register peer IP:Port |
| `http://127.0.0.1:9000/get-list` | View all registered peers (JSON) |
| `http://127.0.0.1:9001/active-peers` | Peer list for VoPham |
| `http://127.0.0.1:9001/view-my-channels` | Connected channels for VoPham |
| `http://127.0.0.1:9001/chat?peer=MinhDuc&ip=127.0.0.1&port=9002` | Chat: VoPham → MinhDuc |
| `http://127.0.0.1:9002/chat?peer=VoPham&ip=127.0.0.1&port=9001` | Chat: MinhDuc → VoPham |



## Features

### 2.1 Non-blocking Mechanism

The server supports three concurrent connection models, switchable via `mode_async` in `backend.py`:

| Mode | Implementation | Description |
|------|---------------|-------------|
| `threading` | `threading.Thread` per connection | Default mode; each client gets its own thread |
| `coroutine` | `asyncio` + `async/await` | Single-threaded async I/O; non-blocking event loop |
| `callback` | `selectors.DefaultSelector` | Event-driven; one thread monitors multiple sockets |

### 2.2 HTTP Authentication

Cookie-based authentication per RFC 6265 / RFC 7235:

- `POST /login` validates credentials against SQLite DB, sets `Set-Cookie: auth=true; Path=/`
- All protected `.html` pages check `req.cookies["auth"] == "true"` on every request
- Missing or invalid cookie returns `HTTP/1.1 401 Unauthorized`
- Public pages exempt from auth: `/login.html`, `/submit.html`

### 2.3 Hybrid Chat Application

**Phase 1 – Tracker (Client-Server):**
- Peers register their `ip:port` with the Tracker via `POST /submit-info`
- Tracker maintains an in-memory `peer_list` dict
- Any peer can query `GET /get-list` to discover all online peers

**Phase 2 – P2P Direct Messaging:**
- Each peer runs its own HTTP server
- Messages sent via `POST /receive-message` directly to target peer's IP:Port
- No Tracker involvement after initial discovery
- Chat history stored in-memory per peer pair
- Frontend polls `GET /get-messages?peer=<name>` every 1 second

**CLI Multi-channel (bonus):**
- Peer can join multiple Tracker channels simultaneously
- `/broadcast` sends to all peers across all joined channels
- `/msg <username>` sends a private 1-to-1 message
- Channel membership persisted in `<username>_channels.json`



## API Reference

### Tracker Endpoints (`start_tracker.py`)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/login` | Serve login form |
| `POST` | `/login` | Validate credentials, set auth cookie |
| `GET` | `/submit-info` | Serve IP:Port registration form |
| `POST` | `/submit-info` | Register peer IP:Port into `peer_list` |
| `GET` | `/get-list` | Return all registered peers as JSON |
| `POST` | `/logout` | Remove peer from `peer_list` |
| `POST` | `/save-tracker` | Save tracker IP:Port to `tracker.json` |

### Peer Endpoints (`start_peer.py`)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/add-list` | Add a peer to local BiMap (connect) |
| `POST` | `/receive-message` | Receive a message from another peer |
| `POST` | `/send-message` | Send a message to a peer (saves to local history) |
| `GET` | `/get-messages?peer=<name>` | Retrieve chat history with a specific peer |
| `GET` | `/get-connected-peer` | Return local BiMap as JSON |
| `GET` | `/get-tracker` | Return tracker IP:Port from `tracker.json` |
| `GET` | `/active-peers` | Serve active-peers.html |
| `GET` | `/view-my-channels` | Serve view-my-channels.html |
| `GET` | `/chat` | Serve chat.html |

---

## CLI Commands

Available in `start_peer_cli.py`:

### Channel Management

| Command | Description | Example |
|---------|-------------|---------|
| `/join <ip:port>` | Join a tracker channel and register | `/join 127.0.0.1:8001` |
| `/leave <ip:port>` | Leave a channel and deregister | `/leave 127.0.0.1:8001` |
| `/list_channels` | Show all currently joined channels | `/list_channels` |

### Messaging

| Command | Description | Example |
|---------|-------------|---------|
| `/msg <username> <text>` | Send private P2P direct message | `/msg MinhDuc hello` |
| `/send <ip:port> <text>` | Send to all peers in a specific channel | `/send 127.0.0.1:8001 hello channel` |
| `/broadcast <text>` | Send to all peers in all joined channels | `/broadcast system announcement` |

### Utilities

| Command | Description |
|---------|-------------|
| `/list` | Show all known peers across all channels |
| `/quit` | Logout from all channels and exit |


## Account Management

User credentials are stored in `db/account.db` (SQLite).

### Default accounts

| Username | Password |
|----------|----------|
| VoPham | 2313946 |
| MinhDuc | 2310797 |
| TrungQuan | 2312817 |
| MinhKhang | 2311399 |
| ChanKien | 2211740 |

### Management CLI (`db/account.py`)

```bash
# List all accounts
python db/account.py list

# Add a new account
python db/account.py add <username> <password>

# Delete an account
python db/account.py delete <username>

# Reset all accounts (requires confirmation)
python db/account.py reset
```


## Technical Design

### AsynapRous Framework

A minimal web framework built on raw TCP sockets, inspired by Flask's routing API:

```python
app = AsynapRous()

@app.route('/api/endpoint', methods=['GET', 'POST'])
def handler(req):
    return Response().build_success({"status": "ok"})

app.prepare_address('127.0.0.1', 9000)
app.run()
```

The decorator registers `(METHOD, path) → handler` into a routing table. `HttpAdapter` looks up this table on every incoming request and dispatches accordingly, falling back to static file serving if no route matches.

### BiMap (Peer Management)

Each peer maintains a bidirectional map for O(1) lookup in both directions:

```
username  ──►  (ip, port)
(ip, port) ──►  username
```

This allows efficient lookup whether you know the username or the network address.

### Directory Traversal Protection

`Response.build_content()` uses `os.path.realpath()` to resolve the final file path and verifies it stays within the allowed `base_dir` before reading. Any attempt to escape via `../` is rejected.

### Proxy Configuration

`config/proxy.conf` uses an NGINX-inspired syntax:

```nginx
host "app.local" {
    proxy_pass http://127.0.0.1:9001;
    proxy_pass http://127.0.0.1:9002;
    dist_policy round-robin;
}
```

`start_proxy.py` parses this file at startup and builds a routing table. Incoming requests are forwarded to backends using round-robin selection with thread-safe counters.

---

## License

Copyright (C) 2026 pdnguyen — HCMC University of Technology (VNU-HCM).  
For educational use in CO3093/CO3094 only.
