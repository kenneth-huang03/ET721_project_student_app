# LMS Application


## Project structure

```
project/
├── app.py                  Flask application: routes, DB
├── README.md               Current File
├── lms.sqlite3             SQLite database
│
├── static/
│   ├── style.css           All page styles 
│   ├── script.js           Javascript for flash auto-dismiss, delete confirmations, file-input
│   │                           feedback, and submit-button guarding
│   └── uploads/            Stored uploads
│
└── templates/
    ├── base.html           Shared layout
    ├── login.html          Login form
    ├── dashboard.html      Dashboard Page
    ├── todo.html           Per User To-do list with add/complete/delete capabilities
    ├── blogs.html          Public blog feed with add/delete capabilities
    ├── file-share.html     File list + upload form
    └── file-view.html      Per-file viewer page with inline preview and a Download button
```

---

## Setup and installation

### Prerequisites

- Python 3.10+ (anything that supports modern Flask works; 3.11+ recommended)
- `pip`

### 1. Clone or download the project

```
cd path/to/folder
# place the ET721_project_student_app folder here
cd ET721_project_student_app
```

### 2. Create and activate a virtual environment

Windows (PowerShell):

```
python -m venv .venv
.venv\Scripts\Activate.ps1
```

macOS / Linux:

```
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```
pip install Flask==3.1.3
```

This installs Flask along with its transitive dependencies (Werkzeug, Jinja2, click, itsdangerous, blinker, MarkupSafe).

---

## Running the application

From the project directory with the virtual environment active:

```
python app.py
```

By default Flask binds to `http://127.0.0.1:5000/`. Open that URL in a browser. The root path redirects to the login page.

### First-run behavior

On the very first run, `app.py` checks to see if `lms.sqlite3` exists. If it does not exist, it will make three demo accounts so you can log in immediately:

| Username    | Password    | Name        |
| ----------- | ----------- | ----------- |
| `admin`     | `admin`     | Admin User  |
| `professor` | `professor` | Prof Smith  |
| `student`   | `student`   | John Doe    |


> [!CAUTION]
> **Passwords are stored as plaintext in this project for simplicity.**
>
> For any real deployment, hash passwords (e.g. with `werkzeug.security.generate_password_hash`) and set a real `SECRET_KEY` via environment variable rather than the placeholder string.

### Where uploaded files go

Files uploaded through `/file-share` are written to `static/uploads/`.

The viewer page (`/file-share/<file_id>`) dispatches by extension:

- **Image**: shown via `<img>`
- **PDF**: shown via `<iframe>` (browser PDF viewer)
- **Audio / Video**: shown via `<audio controls>` / `<video controls>`
- **Text-like** (txt, csv, tsv, md, tex, bib, ipynb, json, xml, log): first 256 KB read server-side and rendered in a `<pre>` (Jinja auto-escaping protects against HTML/script content inside the file)
- **Office / archive / other**: "preview not available" placeholder; the Download button is still available

### Stopping the server

`Ctrl+C` in the terminal running `python app.py`.

### Resetting the database

Stop the server, delete `lms.sqlite3` (and optionally, but **suggested** `static/uploads/`), and start the app again. It will re-seed the demo users and recreate empty tables.
