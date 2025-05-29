# Buddy
Learning project build upon the GPT api


## Getting Started

### 1. Clone the repo

```bash
git clone https://github.com/njyeung/Buddy
cd Buddy
```

### 2. Frontend

#### a. (For development) Start server:

```bash
# From project root
cd frontend
npm install
npm run dev
```

**Make sure the localhost port matches the one in `main.c`:**

```c
// line 139
webview_navigate(w, "http://localhost:5173");
```

#### b. Or point towards built contents

If you’ve run `npm run build`, update `main.c` to point to the built bundle instead (i.e. a local file path), and rebuild the bridge executable (see step 4).

---

### 3. Install backend Python libraries

```bash
# From project root
cd backend
pip install -r requirements.txt
```

> You don’t need to run the backend manually. The C program will spawn it as a child process.
> So if you change the Python code, just restart the executable. It’s fast because webview is lightweight.

---

### 4. Run the executable to launch the app

* **For Windows:**
  `Buddy.exe`

* **For macOS:**
  *(Not done yet, I need to write that ;-;)*

* **For Linux:**
  *(HELP)*

---

### 5. (Optional) If you intend to modify the C bridge: Install webview submodule

Buddy uses webview to bridge the backend (Python) and frontend (React) via native pipes and threads. It’s not registered as a submodule, so you will need to:

#### a. Clone the webview repository manually

```bash
# From the Buddy root
git clone https://github.com/webview/webview
```

#### b. Make sure you install all of webview’s dependencies for your platform

See: [https://github.com/webview/webview](https://github.com/webview/webview)

#### c. Make changes to the bridge code located in the root directory

```bash
# Root directory
./main.c
```

> For Windows, I made a Makefile to clean, configure, build, and copy the binary into the project root as `Buddy.exe`.
> For macOS or Linux… good luck 😅

```bash
Run “make”
```

---

Let me know when you’re ready to move on to the next section!

