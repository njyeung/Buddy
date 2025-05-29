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

---

## Concepts of Projects, Chats, Messages, RAGs, Sliding Window, and User Profile

### 1. Persistent Chat History

All messages are stored in an SQL database, structured around a `projects` table, `chats` table, and `messages` table, where each message is associated with a `chat_id` and each chat is associated with a `project_id`. This enables support of multiple, independent conversations, each with its own navigable history ready to be displayed on the frontend.

In addition, projects help users organize related chats in a single folder.

![ER diagram of project/chat/message/vector schema]()
*Figure a*

---

### 2. Retrieval-Augmented Generation (RAG)

For enhanced contextual awareness across chats, Buddy implements RAG. However, instead of using RAG to retrieve messages from the current chat (which is already summarized using the sliding window approach—see section 4), we pull semantically similar messages from other chats within the same project (or globally, depending on config).

This enables the language model to incorporate meaningful information from other interactions and deliver more intelligent, context-aware responses, while also letting the user control what it should “remember.”

#### How it works:

a. Important messages are vectorized and stored in a vector DB along with metadata tags (see figure a).
b. When a user inputs a new message, it is vectorized and used to query the vector DB for semantically relevant messages where `chat_id != current_chat_id` and `project_id == current_project_id`.
c. Each matching vector includes a metadata tag with the original `message_id`, which is used to retrieve the original message from the SQL database.
d. These retrieved messages are injected into the prompt as ephemeral memory.

> These retrieved messages are not persisted and do not affect the conversation history—they’re injected just-in-time to influence the model for a better response.

---

### 3. User Profile

Along with the initial system prompt, we also maintain a global user profile. This editable JSON includes traits such as:

* User’s name
* Country
* Preferred frameworks/languages
* Current projects and descriptions
* And more

Buddy uses liberal filtering to identify potentially “important” messages and queues them. When the queue grows large enough, we asynchronously distill the messages into profile updates.

This hybrid system balances transparency and automation: users can manually edit their profile or set an entirely new one at any time, while the assistant progressively builds a richer understanding of the user over time without manual intervention.

---

### 4. Sliding Window Summarization

To manage context length and token usage efficiently, Buddy employs a sliding window mechanism that periodically summarizes earlier parts of a conversation. The overall context structure follows this format:

```
a) Initial system prompt
b) User profile         # Manually editable by the user
c) Dynamic summary      # Unique per chat
d) Earlier messages     # To be summarized in sliding window
e) Most recent X messages  # Always kept intact
f) RAG messages         # If applicable
```

> 📌 *Diagram shown in README image above.*

Recent X messages (e) — configurable via `NUM_RECENT_MESSAGES_TO_KEEP` in [`config.py`](./backend/config.py) (default: 7) — are always preserved to maintain the most up-to-date context.

Whenever the combined character count from the start of the **dynamic summary system prompt** to the start of the **recent messages** exceeds N characters (set via `SUMMARY_TRIGGER_CHAR_COUNT` in [`config.py`](./backend/config.py), default: 5000), that section (c–d) is summarized by the slave model. The resulting summary replaces the original messages from that section.

As noted earlier, **RAG messages** (f) are ephemeral — they are injected just-in-time for the current API call and are not persisted in the chat history.

---

**The sliding window sits one level higher in granularity** than the recent messages and RAG snippets — it distills broader conversational context. However, it remains **below the user profile system prompt**, which contains long-term, cross-chat knowledge.

These summarized threads — system prompt, user profile, dynamic summary, and recent messages — are stored in the SQL database and automatically reloaded when the user returns to a chat. This lets the assistant resume where it left off and maintain continuity.
