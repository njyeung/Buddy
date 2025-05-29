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
  `./Buddy`

* **For Linux:**
  `./Buddy`

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

> I made a Makefile to clean, configure, build, and copy the binary into the project root as `Buddy.exe`.

```bash
Run “make”
```

---

### (Optional) Preload API keys

Buddy’s backend will automatically prompt you for API keys when needed—so you don’t have to configure everything up front. For example, if you use the Spotify tool and don’t have credentials yet, Buddy will ask and save them for future use.

However, if you'd like to set things up manually ahead of time:

* Create a `.env` file in `/backend/`

* Add your OpenAI API key:

  ```env
  OPENAI=your-openai-api-key
  ```

* As well as keys for any tools you plan to use (see **Tools** below for an example on how to create your own tools):

  ```env
  SERPAPI_API_KEY=your-serpapi-key
  SPOTIFY_CLIENT_ID=your-spotify-client-id
  MY_EXAMPLE_TOOL_KEY=your-tool-key
  # ...etc
  ```

