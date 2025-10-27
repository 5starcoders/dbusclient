# PySide6 One-Click D-Bus User Creator

## 📖 Overview
This project is a **graphical D-Bus client** built using **PySide6 (Qt for Python)**.  
Its primary goal is to let a user create new Linux system users via the **`org.freedesktop.Accounts`** service — with a single button click.

While the initial version focuses only on **user creation**, the entire architecture is designed to be **modular and expandable**.  
Later, additional D-Bus services such as **`org.freedesktop.timedate1`**, **`org.freedesktop.NetworkManager`**, and others can be added dynamically.

---

## 🧩 Core Idea
- Show one button in a minimal GUI window.  
- When clicked:
  1. A predefined username, real name, and password are used.
  2. The app connects to the **system D-Bus**.
  3. It calls `org.freedesktop.Accounts.CreateUser()` to create the account.
  4. It then calls `org.freedesktop.Accounts.User.SetPassword()` to assign the password.
  5. A success or error message is displayed to the user.

The architecture follows a **clean layered approach** that separates UI, logic, D-Bus calls, and configuration for maintainability.

---

## 🏗️ Architecture Overview
```
run_app.py
│
└── app/
    ├── ui/
    │   └── main_window.py           → GUI components (PySide6 widgets)
    │
    ├── actions/
    │   └── create_user_action.py    → Orchestrates the workflow (create + password)
    │
    ├── services/
    │   └── accounts/
    │       └── adapter.py           → Contains actual D-Bus method calls for Accounts
    │
    └── dbus/
        ├── bus_manager.py           → Manages connection to the D-Bus system bus
        └── invoker.py               → Handles sending/receiving D-Bus method calls
│
├── config/
│   └── services.json                → Registry for D-Bus service info (hard-coded now)
│
├── cache/
│   └── introspection/               → Placeholder for future XML interface caching
│
└── logs/                            → Runtime logs or error traces (optional)
```

### ✳️ Layer Responsibilities
| Layer | Description |
|-------|--------------|
| **UI (main_window.py)** | Handles all visual elements and user interactions (buttons, popups). |
| **Actions (create_user_action.py)** | Coordinates tasks between UI and service adapters. |
| **Services (adapter.py)** | Implements specific D-Bus calls for one service. |
| **D-Bus Core (bus_manager & invoker)** | Provides reusable connection and call helpers for all services. |
| **Config (services.json)** | Stores bus names, object paths, and interface details. |

This modular structure ensures that adding a new service (e.g., `timedate1`) requires only a new adapter and an entry in `services.json`.

---

## 🧱 Step-by-Step Implementation Plan

### **Phase 1 — Environment Setup**
1. Create a virtual environment using `python3 -m venv .venv`.
2. Activate it using `source .venv/bin/activate`.
3. Upgrade pip: `python -m pip install --upgrade pip`.
4. Install PySide6: `pip install PySide6`.
5. Verify installation: `python -c "import PySide6; print(PySide6.__version__)"`.

### **Phase 2 — Project Skeleton**
Manually create directories and empty files:

```bash
mkdir -p app/{ui,actions,services/accounts,dbus} config cache/introspection logs
touch app/ui/main_window.py
touch app/actions/create_user_action.py
touch app/services/accounts/adapter.py
touch app/dbus/bus_manager.py
touch app/dbus/invoker.py
touch config/services.json
touch run_app.py
```

### **Phase 3 — Bring Up GUI**
- Display a simple PySide6 window with one button.
- Handle the click event (connect Qt *signal* → Python *slot*).

### **Phase 4 — Connect to System D-Bus**
- Use PySide6’s `QtDBus` module to connect to the **system bus**.
- Prepare a `BusManager` class that provides one shared connection.

### **Phase 5 — Implement AccountsService Adapter**
- Call `CreateUser(username, realname, accountType:int32)`  
  Returns: object path of the created user.
- Call `User.SetPassword(hash, hint)`  
  Uses a **SHA-512 shadow-style hash** for security.
- Ensure the password is never stored or logged in plaintext.

### **Phase 6 — Add Orchestration Layer**
- Combine both D-Bus calls inside `create_user_action.py`.
- Display success or failure back to the GUI.

### **Phase 7 — Validation and Logging**
- Add logging under `/logs/`.
- Catch D-Bus or Polkit errors (e.g., insufficient privileges).

### **Phase 8 — Scalability Hooks**
- Introduce `services.json` registry:
  ```json
  {
    "accounts": {
      "bus": "system",
      "name": "org.freedesktop.Accounts",
      "rootPath": "/org/freedesktop/Accounts"
    }
  }
  ```
- Later: replace static config with a **dynamic service discovery** that scans available D-Bus services.

---

## ⚙️ Runtime Flow
1. **User clicks button** → signal triggers slot in main window.
2. **Action Layer** called → runs `create_user_action`.
3. **Action** calls `adapter.create_user()` → D-Bus call to AccountsService.
4. Adapter receives returned user object path.
5. **Action** calls `adapter.set_password()` for that path.
6. **Result** displayed in GUI and logged in `/logs/`.

---

## 🔐 Security Considerations
- The password is hashed in memory only (using SHA-512 shadow format).
- No plaintext password written to disk.
- D-Bus calls may trigger a **Polkit authentication dialog**; approve with an administrator account.
- Future versions can integrate with the user’s **Gatekeeper** or custom policy engine.

---

## 🧠 Learning Curve for Python and Qt
Because the developer may be new to Python:
- Each step will include a short explanation of **Python syntax** used.
- You’ll learn:
  - Basic Python scripting and modules.
  - Object-oriented programming with classes.
  - PySide6 event loop (signals and slots).
  - QtDBus usage for system communication.

---

## 🪄 Future Expansion
| Module | Description |
|---------|--------------|
| **timedate** | Control system time, NTP, and timezone via `org.freedesktop.timedate1`. |
| **network** | Manage network interfaces through NetworkManager or systemd-networkd. |
| **discovery** | Dynamically introspect available D-Bus services. |
| **policy** | Integrate a ruleset or Gatekeeper module to control which users can trigger which calls. |

All future features will follow the same modular pattern:  
**new adapter → new action → optional UI element.**

---

## 🧰 Useful Commands for Validation
```bash
# View live D-Bus traffic for AccountsService
dbus-monitor --system "destination='org.freedesktop.Accounts' || sender='org.freedesktop.Accounts'"

# Introspect available methods
busctl introspect org.freedesktop.Accounts /org/freedesktop/Accounts

# Verify created user
getent passwd <username>
id <username>
```

---

## 🧩 Dependencies Summary
| Package | Purpose |
|----------|----------|
| **PySide6** | GUI + QtDBus framework for Python |
| **Python 3.10+** | Primary runtime |
| **Polkit (system)** | Authentication for privileged D-Bus actions |
| **AccountsService** | Backend D-Bus daemon for user management |

---

## 🧭 Key Principles
1. **Modularity:** each service and action isolated in its own file.
2. **Security:** no plaintext secrets, follow Polkit.
3. **Scalability:** one architecture for all D-Bus services.
4. **Clarity:** well-commented, beginner-friendly Python code.
5. **Maintainability:** extend without breaking existing modules.

---

## 🧑‍💻 Author Notes
This project is meant to be both a **learning journey in Python & Qt** and a **foundation for a professional-grade modular D-Bus GUI client**.  
Every step will be small, explained, and logically connected to the previous one.

When the base “Create User” feature works, the same framework can power a complete system-management dashboard for KDE or other desktops.

---
