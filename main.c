#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>
#include <webview/webview.h>

#ifdef _WIN32
    #define WEBVIEW_WINAPI
    #include <windows.h>
    #include <winsock2.h>
    #include <ws2tcpip.h>
    #include <direct.h>
    #include <sys/stat.h>
#else
    #include <unistd.h>
    #include <pthread.h>
    #include <sys/stat.h>
    #include <sys/wait.h>
    #include <sys/socket.h>
    #include <netinet/in.h>
    #include <arpa/inet.h>
#endif

// Global variables for cleanup
pid_t frontend_server_pid = 0;
pid_t audio_service_pid = 0;
pid_t python_backend_pid = 0;
char* dev_mode = NULL;

void cleanup_servers() {
    printf("\nCleaning up servers...\n");
    
    #ifdef _WIN32
    // Windows cleanup - kill processes by name/port
    system("taskkill /f /im python.exe 2>nul");
    if(dev_mode && strcmp(dev_mode, "1") == 0) {
        system("for /f \"tokens=5\" %a in ('netstat -aon ^| find \":8080\"') do taskkill /f /pid %a 2>nul");
    }
    system("for /f \"tokens=5\" %a in ('netstat -aon ^| find \":8081\"') do taskkill /f /pid %a 2>nul");
    #else
    // Linux cleanup - kill tracked PIDs
    if (audio_service_pid > 0) {
        printf("Stopping audio service (PID: %d)\n", audio_service_pid);
        kill(audio_service_pid, SIGTERM);
        waitpid(audio_service_pid, NULL, WNOHANG);
    }
    if(dev_mode && strcmp(dev_mode, "1") == 0) {
        if (frontend_server_pid > 0) {
            printf("Stopping frontend server (PID: %d)\n", frontend_server_pid);
            kill(frontend_server_pid, SIGTERM);
            waitpid(frontend_server_pid, NULL, WNOHANG);
        }
    }
    
    if (python_backend_pid > 0) {
        printf("Stopping python backend (PID: %d)\n", python_backend_pid);
        kill(python_backend_pid, SIGTERM);
        waitpid(python_backend_pid, NULL, WNOHANG);
    }
    
    // Fallback: kill anything on our ports
    system("pkill -f 'python.*main.py' 2>/dev/null");
    system("pkill -f 'python.*http.server.*8080' 2>/dev/null");
    #endif
}

void signal_handler(int sig) {
    printf("\nShutting down gracefully...\n");
    cleanup_servers();
    exit(0);
}

int port_in_use(int port) {
    #ifdef _WIN32
    WSADATA wsaData;
    WSAStartup(MAKEWORD(2, 2), &wsaData);
    
    SOCKET sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock == INVALID_SOCKET) {
        WSACleanup();
        return 0;
    }
    
    struct sockaddr_in addr;
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = inet_addr("127.0.0.1");
    addr.sin_port = htons(port);
    
    int result = bind(sock, (struct sockaddr*)&addr, sizeof(addr));
    closesocket(sock);
    WSACleanup();
    
    // port in use if bind failed
    return result != 0;

    #else
    
    int sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock < 0) {
        return 0;
    }
    
    struct sockaddr_in addr;
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = inet_addr("127.0.0.1");
    addr.sin_port = htons(port);
    
    int result = bind(sock, (struct sockaddr*)&addr, sizeof(addr));
    close(sock);
    
    // Port in use if bind failed
    return result != 0; 
    #endif
}

void send_text_to_audio_service(const char* text) {
    // Create a temporary file with the JSON payload to avoid shell escaping issues
    #ifdef _WIN32
    char temp_file[256];
    snprintf(temp_file, sizeof(temp_file), "%s\\buddy_tts_%d.json", getenv("TEMP") ? getenv("TEMP") : "C:\\temp", (int)GetCurrentProcessId());
    
    FILE* f = fopen(temp_file, "w");
    if (!f) return;
    fprintf(f, "{\"text\": \"");
    
    // Escape JSON special characters
    for (const char* p = text; *p; p++) {
        if (*p == '"' || *p == '\\') {
            fputc('\\', f);
        }
        fputc(*p, f);
    }
    fprintf(f, "\"}");
    fclose(f);
    
    char cmd[512];
    snprintf(cmd, sizeof(cmd), 
        "curl -s -X POST http://127.0.0.1:8081/api/tts "
        "-H \"Content-Type: application/json\" "
        "-d @\"%s\" "
        "-o nul 2>nul && del \"%s\" &", temp_file, temp_file);
    system(cmd);
    #else
    char temp_file[256];
    snprintf(temp_file, sizeof(temp_file), "/tmp/buddy_tts_%d.json", getpid());
    
    FILE* f = fopen(temp_file, "w");
    if (!f) return;
    fprintf(f, "{\"text\": \"");
    
    // Escape JSON special characters
    for (const char* p = text; *p; p++) {
        if (*p == '"' || *p == '\\') {
            fputc('\\', f);
        }
        fputc(*p, f);
    }
    fprintf(f, "\"}");
    fclose(f);
    
    char cmd[512];
    snprintf(cmd, sizeof(cmd), 
        "curl -s -X POST http://127.0.0.1:8081/api/tts "
        "-H 'Content-Type: application/json' "
        "-d @%s "
        ">/dev/null 2>&1; rm %s &", temp_file, temp_file);
    system(cmd);
    #endif
}

// Simple function to check if message is assistant-message and extract payload
char* extract_assistant_message(const char* json_line) {
    // Look for "type": "assistant-message"
    if (strstr(json_line, "\"type\": \"assistant-message\"") == NULL) {
        return NULL;
    }
    
    // Find payload field
    const char* payload_start = strstr(json_line, "\"payload\": \"");
    if (payload_start == NULL) {
        return NULL;
    }
    
    payload_start += 12; // Move past "payload": "
    
    // Find end of payload (next unescaped quote)
    const char* payload_end = payload_start;
    while (*payload_end && *payload_end != '"') {
        if (*payload_end == '\\' && *(payload_end + 1)) {
            payload_end += 2; // Skip escaped character
        } else {
            payload_end++;
        }
    }
    
    if (*payload_end != '"') {
        return NULL;
    }
    
    // Extract payload text
    size_t len = payload_end - payload_start;
    char* result = malloc(len + 1);
    if (!result) return NULL;
    
    strncpy(result, payload_start, len);
    result[len] = '\0';
    
    return result;
}

typedef struct
{
#ifdef _WIN32
    HANDLE stdinWrite;
    HANDLE stdoutRead;
#else
    int stdinWrite;
    int stdoutRead;
#endif
    webview_t w;
} PipeHandles;

#ifdef _WIN32
    void print_utf8(const char *utf8)
    {
        HANDLE hConsole = GetStdHandle(STD_OUTPUT_HANDLE);
        int wlen = MultiByteToWideChar(CP_UTF8, 0, utf8, -1, NULL, 0);
        wchar_t *wstr = (wchar_t *)malloc(wlen * sizeof(wchar_t));
        if (!wstr)
            return;
        MultiByteToWideChar(CP_UTF8, 0, utf8, -1, wstr, wlen);
        DWORD written;
        WriteConsoleW(hConsole, wstr, wlen - 1, &written, NULL);
        free(wstr);
    }
#else
    void print_utf8(const char* msg){
        printf("%s", msg);
    }
#endif

// On data from React frontend
static void producer(const char *seq, const char *req, void *arg)
{
    PipeHandles *pipes = (PipeHandles *)arg;

    #ifdef _WIN32
        DWORD written;
        WriteFile(pipes->stdinWrite, req, strlen(req), &written, NULL);
        WriteFile(pipes->stdinWrite, "\n", 1, &written, NULL);
    #else
        dprintf(pipes->stdinWrite, "%s\n", req);
    #endif
}

static void output(webview_t w, void *arg)
{
    const char *msg = (const char *)arg;
    size_t len = strlen(msg);
    if (len > 0 && msg[len - 1] == '\n')
    {
        ((char *)msg)[len - 1] = '\0';
    }
    char js[32768];
    snprintf(js, sizeof(js), "receiveData(%s);", msg);
    webview_eval(w, js);
    free(arg);
}

// On data from Python backend 
#ifdef _WIN32
    DWORD WINAPI consumer_thread(LPVOID lpParam) {
        PipeHandles *p = (PipeHandles *)lpParam;
        webview_t w = p->w;

        size_t bufferSize = 1024;
        char *buffer = malloc(bufferSize);
        size_t bufferLen = 0;
        if (!buffer) return 0;

        char chunk[1024];
        DWORD bytesRead;

        while (1) {
            if (!ReadFile(p->stdoutRead, chunk, sizeof(chunk) - 1, &bytesRead, NULL)) break;
            chunk[bytesRead] = '\0';

            if (bufferLen + bytesRead + 1 >= bufferSize) {
                bufferSize = (bufferLen + bytesRead + 1) * 2;
                buffer = realloc(buffer, bufferSize);
            }
            memcpy(buffer + bufferLen, chunk, bytesRead);
            bufferLen += bytesRead;
            buffer[bufferLen] = '\0';

            char *lineStart = buffer;
            char *newline;
            while ((newline = strchr(lineStart, '\n')) != NULL) {
                *newline = '\0';
                if (strncmp(lineStart, "{\"type\": \"log\"", 16) == 0) {
                    printf("[LOG] %s\n", lineStart);
                    lineStart = newline + 1;
                    continue;
                }
                
                // Check if this is an assistant message and send to audio service
                char* assistant_text = extract_assistant_message(lineStart);
                if (assistant_text) {
                    printf("[TTS] Sending to audio service: %s\n", assistant_text);
                    send_text_to_audio_service(assistant_text);
                    free(assistant_text);
                }
                
                webview_dispatch(w, output, _strdup(lineStart));
                lineStart = newline + 1;
            }

            size_t leftover = buffer + bufferLen - lineStart;
            memmove(buffer, lineStart, leftover);
            bufferLen = leftover;
        }

        free(buffer);
        return 0;
    }
#else
    void* consumer_thread(void* lpParam) {
        PipeHandles *p = (PipeHandles *)lpParam;
        webview_t w = p->w;

        size_t bufferSize = 1024;
        char *buffer = malloc(bufferSize);
        size_t bufferLen = 0;
        if (!buffer) return NULL;

        char chunk[1024];
        ssize_t bytesRead;

        while (1) {
            bytesRead = read(p->stdoutRead, chunk, sizeof(chunk) - 1);
            if (bytesRead <= 0) break;
            chunk[bytesRead] = '\0';

            if (bufferLen + bytesRead + 1 >= bufferSize) {
                bufferSize = (bufferLen + bytesRead + 1) * 2;
                buffer = realloc(buffer, bufferSize);
            }
            memcpy(buffer + bufferLen, chunk, bytesRead);
            bufferLen += bytesRead;
            buffer[bufferLen] = '\0';
            char *lineStart = buffer;
            char *newline;

            printf("[LOG] %s", lineStart);

            while ((newline = strchr(lineStart, '\n')) != NULL) {
                *newline = '\0';
                if (strncmp(lineStart, "{\"type\": \"log\"", 14) == 0) {
                    printf("[LOG] %s\n", lineStart);
                    lineStart = newline + 1;
                    continue;
                }
                
                // Check if this is an assistant message and send to audio service
                char* assistant_text = extract_assistant_message(lineStart);
                if (assistant_text) {
                    printf("[TTS] Sending to audio service: %s\n", assistant_text);
                    send_text_to_audio_service(assistant_text);
                    free(assistant_text);
                }
                
                webview_dispatch(w, output, strdup(lineStart));
                lineStart = newline + 1;
            }

            size_t leftover = buffer + bufferLen - lineStart;
            memmove(buffer, lineStart, leftover);
            bufferLen = leftover;
        }

        free(buffer);
        return NULL;
    }
#endif

int build_frontend() {
    printf("Checking if dist exists\n");

    #ifdef _WIN32
    struct stat st;
    if(stat("frontend\\dist", &st) != 0) {
        printf("Frontend dist not found. Building static files\n");

        int err = system("cd frontend && npm install && npm run build");
        if(!err) {
            return err;
        }
    }
    #else
    struct stat st;
    if (stat("frontend/dist", &st) != 0) {
        printf("Frontend distnot found. Building static files\n");

        int err = system("cd frontend && npm install && npm run build");
        if(!err) {
            return err;
        }
    }
    #endif

    printf("Static files built\n");

    return 0;
}

int setup_python_venv() {
    printf("Checking Python virtual environment\n");
    
    #ifdef _WIN32
    struct stat st;
    if (stat("backend\\venv", &st) != 0) {
        printf("Virtual environment not found. Creating venv\n");

        int err = system("cd backend && python -m venv venv");
        if (!err) {
            return err;
        }
        printf("Virtual environment created\n");
    }
    printf("Installing/updating dependencies...\n");
    
    system("cd backend && call venv\\Scripts\\activate && pip install -r requirements.txt");
    if (!err) {
        return err;
    }

    #else
    
    struct stat st;
    if (stat("backend/venv", &st) != 0) {
        printf("Virtual environment not found. Creating venv\n");
        
        int err = system("cd backend && python -m venv venv");
        if (!err) {
            return err;
        }

        printf("Virtual environment created\n");
    }
    printf("Installing/updating dependencies\n");
    
    int err = system("cd backend && source venv/bin/activate && pip install -r requirements.txt");
    if (!err) {
        return err;
    }
    #endif
    
    printf("Python environment ready. Starting backend\n");

    return 0;
}

int start_audio_service() {
    printf("Checking audio service virtual environment\n");
    
    #ifdef _WIN32
    // Check if audio-service directory exists
    struct stat st;
    if (stat("audio-service", &st) != 0) {
        printf("Audio service directory not found\n");
        exit(1);
    }
    
    // Check if venv exists, create if not
    if (stat("audio-service\\venv", &st) != 0) {
        printf("Audio service virtual environment not found. Creating venv\n");
        
        int err = system("cd audio-service && python -m venv venv");
        if (err != 0) {
            printf("Could not create audio service venv\n");
            exit(1);
        }
        printf("Audio service virtual environment created\n");
    }
    
    printf("Installing/updating audio service dependencies\n");
    int err = system("cd audio-service && call venv\\Scripts\\activate && pip install -r requirements.txt");
    if (err != 0) {
        printf("Could not install audio service dependencies\n");
        exit(1);
    }
    
    printf("Audio service environment ready. Starting audio service\n");
    if (system("start /B cmd /C \"cd audio-service && call venv\\Scripts\\activate && python main.py\"") != 0) {
        printf("Could not start audio service\n");
        exit(1);
    }
    Sleep(2000);
    #else
    // Check if audio-service directory exists  
    struct stat st;
    if (stat("audio-service", &st) != 0) {
        printf("Audio service directory not found\n");
        exit(1);
    }
    
    // Check if venv exists, create if not
    if (stat("audio-service/venv", &st) != 0) {
        printf("Audio service virtual environment not found. Creating venv\n");
        
        int err = system("cd audio-service && python3 -m venv venv");
        if (err != 0) {
            printf("Could not create audio service venv\n");
            exit(1);
        }
        printf("Audio service virtual environment created\n");
    }
    
    printf("Installing/updating audio service dependencies\n");
    int err = system("cd audio-service && source venv/bin/activate && pip install -r requirements.txt");
    if (err != 0) {
        printf("Could not install audio service dependencies\n");
        exit(1);
    }
    
    printf("Audio service environment ready. Starting audio service\n");
    if (system("cd audio-service && source venv/bin/activate && python3 main.py &") != 0) {
        printf("Could not start audio service\n");
        exit(1);
    }
    sleep(2);
    #endif
    
    printf("Audio service started on port 8081\n");
    return 0;
}

int main()
{
    // Register signal handlers for cleanup
    signal(SIGINT, signal_handler);   // Ctrl+C
    signal(SIGTERM, signal_handler);  // Termination
    #ifndef _WIN32
    signal(SIGHUP, signal_handler);   // Terminal hangup
    #endif
    
    dev_mode = getenv("DEV_MODE");
    
    // Check if required ports are available
    if (port_in_use(8081)) {
        printf("Error: Port 8081 is already in use. Audio service cannot start.\n");
        exit(1);
    }
    
    if (!(dev_mode && strcmp(dev_mode, "1") == 0)) {
        if (port_in_use(8080)) {
            printf("Error: Port 8080 is already in use. Frontend server cannot start.\n");
            exit(1);
        }
    }
    
    if (start_audio_service() != 0) {
        printf("could not start audio service\n");
        exit(1);
    }


    setenv("GDK_BACKEND", "wayland", 1);
    setenv("WEBKIT_DISABLE_DMABUF_RENDERER", "1", 1);
    setenv("WEBKIT_DISABLE_COMPOSITING_MODE", "1", 1);

    webview_t w = webview_create(0, NULL);
    webview_set_title(w, "Buddy");
    webview_set_size(w, 600, 800, WEBVIEW_HINT_NONE);

    if(dev_mode && strcmp(dev_mode, "1") == 0) {
        webview_navigate(w, "http://localhost:5173");
    }
    else {
        // build static files if needed
        if (build_frontend() != 0) {
            printf("could not build frontend\n");
            exit(1);
        }

        // Serve static files with http server
        #ifdef _WIN32
        if (system("start /B cmd /C \"cd frontend\\dist && python -m http.server 8080\"") != 0) {
            printf("could not start server\n");
            exit(1);
        }
        Sleep(2000);
        #else
        if (system("cd frontend/dist && python3 -m http.server 8080 --bind 127.0.0.1 &") != 0) {
            printf("could not start server\n");
            exit(1);
        }
        sleep(2);
        #endif
        
        webview_navigate(w, "http://127.0.0.1:8080");
    }

    // Set up venv if one doesn't exist
    if (setup_python_venv() != 0) {
        printf("could not set up python venv\n");
        exit(1);
    }

    PipeHandles pipeHandles;

    #ifdef _WIN32
        // No clue what this does, windows is crazy bruh

        SECURITY_ATTRIBUTES sa = {sizeof(SECURITY_ATTRIBUTES), NULL, TRUE};
        HANDLE hChildStdoutRd, hChildStdoutWr;
        HANDLE hChildStdinRd, hChildStdinWr;
        CreatePipe(&hChildStdoutRd, &hChildStdoutWr, &sa, 0);
        SetHandleInformation(hChildStdoutRd, HANDLE_FLAG_INHERIT, 0);
        CreatePipe(&hChildStdinRd, &hChildStdinWr, &sa, 0);
        SetHandleInformation(hChildStdinWr, HANDLE_FLAG_INHERIT, 0);

        STARTUPINFO si = {sizeof(si)};
        PROCESS_INFORMATION pi;
        si.dwFlags = STARTF_USESTDHANDLES;
        si.hStdOutput = hChildStdoutWr;
        si.hStdInput = hChildStdinRd;
        si.hStdError = GetStdHandle(STD_ERROR_HANDLE);

        char cmd[] = "cmd /C \"cd backend && call venv\\Scripts\\activate && python main.py\"";

        if (!CreateProcess(NULL, cmd, NULL, NULL, TRUE, 0, NULL, NULL, &si, &pi))
        {
            fprintf(stderr, "CreateProcess failed: %lu\n", GetLastError());
            return 1;
        }

        CloseHandle(hChildStdoutWr);
        CloseHandle(hChildStdinRd);

        pipeHandles.stdinWrite = hChildStdinWr;
        pipeHandles.stdoutRead = hChildStdoutRd;

    #else
        int stdin_pipe[2], stdout_pipe[2];

        pipe(stdin_pipe);
        pipe(stdout_pipe);
        pid_t pid = fork();

        if(pid < 0) {
            perror("Fork failed");
            exit(1);
        }
        if (pid == 0) {
            // Child process
            
            // Connect pipes
            dup2(stdin_pipe[0], STDIN_FILENO);
            dup2(stdout_pipe[1], STDOUT_FILENO);
            dup2(stdout_pipe[1], STDERR_FILENO);

            // Close unused pipes
            close(stdin_pipe[1]);
            close(stdout_pipe[0]);

            // Exec python backend with venv
            execlp("bash", "bash", "-c", "cd backend && source venv/bin/activate && python3 main.py", NULL);

            perror("exec failed");
            exit(1);
        }

        // Parent process
        python_backend_pid = pid;  // Track backend PID for cleanup
        
        // Connect pipes
        pipeHandles.stdinWrite = stdin_pipe[1];
        pipeHandles.stdoutRead = stdout_pipe[0];

        // Close unused pipes
        close(stdin_pipe[0]);
        close(stdout_pipe[1]);
    #endif

    pipeHandles.w = w;


    // Create thread to listen to python backend
    #ifdef _WIN32
        CreateThread(NULL, 0, consumer_thread, &pipeHandles, 0, NULL);
    #else
        pthread_t tid;
        pthread_create(&tid, NULL, consumer_thread, &pipeHandles);
    #endif

    // Thread to listen to react frontend
    webview_bind(w, "invoke", producer, &pipeHandles);
    
    webview_run(w);

    webview_destroy(w);
    #ifdef _WIN32
        CloseHandle(pipeHandles.stdinWrite);
        CloseHandle(pipeHandles.stdoutRead);
        CloseHandle(pi.hProcess);
        CloseHandle(pi.hThread);
    #else
        close(pipeHandles.stdinWrite);
        close(pipeHandles.stdoutRead);
    #endif

    return 0;
}
