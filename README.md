
## Installation:
requires Python 3.11.7
```
clone repository
cd to repository folder
python3 -m venv .venv
```

----

## Run

serve index.html:
```
cd to repository folder
source .venv/bin/activate
python -m http.server 5500
```

run python server:
```
cd to repository folder
source .venv/bin/activate
uvicorn main:app --reload
```

access the frontend at:
```
http://localhost:5500/index.html
```

---

## Usage

1. paste your API key
2. reload webpage to restart the conversation



