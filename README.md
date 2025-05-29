# Buddy
Learning project build upon the GPT api

## Getting started

**1. Clone the repo**
```
   git clone https://github.com/njyeung/Buddy
   cd Buddy
```
**2. Frontend**
   * (For development) Start server:
```
      # From project root
      cd frontend
      npm install
      npm run dev
```
   Make sure the localhost port matches the one in main.c:
```
      # line 139
      webview_navigate(w, "http://localhost:5173");
```
   * Or point towards built contents
     
      If you’ve run npm run build, update main.c to point to the built bundle instead (i.e. a local file path), and rebuild the bridge executable (see 4).
**3. Install python libraries**
**4. Run the executable to launch the app**
**5. (Optional) If you intend to modify the C bridge: Install webview**
