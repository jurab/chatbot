# Project for an LLM Security Workshop
API keys are stored in a database for an SQL injection demonstration.

---

## Installation
Requires **Python 3.11.7**

## Linux / macOS

### Script Installation
Download `install.zip`  
Unpack it  
Run:

```bash
chmod -x install.sh
./install.sh
````

### Manual Installation

```bash
git clone <repo>
cd <repo>
python3 -m venv .venv
pip install -r requirements.txt
```

---

## Windows

### Script Installation

Download and unzip `install.zip`.

Open **PowerShell as Administrator** and allow script execution:

```powershell
Set-ExecutionPolicy RemoteSigned
```

Then:

```powershell
.\install.ps1
```

### Manual Installation

```powershell
git clone <repo>
cd <repo>
python -m venv .venv
.\.venv\Scripts\activate.ps1
pip install -r requirements.txt
```

---

## Run

## Linux / macOS

### Script Run

Requires executable bit:

```bash
chmod -x run.sh
./run.sh
```

### Manual Run

**Serve the frontend:**

```bash
cd <repo>
source .venv/bin/activate
python -m http.server 5500
```

**Run the backend:**

```bash
cd <repo>
source .venv/bin/activate
uvicorn main:app --reload
```

Access the frontend at:

```
http://localhost:5500/index.html
```

---

## Windows

### Script Run

Run:

```powershell
.\run_chatbot_simple.ps1
```

or, for the full setup version:

```powershell
.\run_chatbot_full.ps1
```

These will:

* activate the virtual environment
* open two PowerShell windows

  * one running `python -m http.server 5500`
  * one running `uvicorn main:app --reload`

### Manual Run

**Frontend:**

```powershell
cd <repo>
.\.venv\Scripts\activate.ps1
python -m http.server 5500
```

**Backend:**

```powershell
cd <repo>
.\.venv\Scripts\activate.ps1
uvicorn main:app --reload
```

Access the frontend at:

```
http://localhost:5500/index.html
```

---

## Usage

1. Paste your API key in the UI
2. Reload the webpage to restart the conversation
