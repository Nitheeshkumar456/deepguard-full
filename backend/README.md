# DeepGuard AI FastAPI Backend

This is the FastAPI backend for the DeepGuard AI Multimodal Authenticity Platform.

## Getting Started

### Prerequisites

- Python 3.10+
- pip

### Installation

1. Create a virtual environment:
   ```bash
   python -m venv venv
   ```

2. Activate the virtual environment:
   - Windows:
     ```bash
     .\venv\Scripts\activate
     ```
   - Unix/macOS:
     ```bash
     source venv/bin/activate
     ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Running the Server

Start the development server with:
```bash
uvicorn app.main:app --reload
```

The API docs will be available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).
