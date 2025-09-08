#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <webview/webview.h>

#ifdef _WIN32
    #define WEBVIEW_WINAPI
    #include <windows.h>
    #include <direct.h>
    #include <sys/stat.h>
#else
    #include <unistd.h>
    #include <pthread.h>
    #include <sys/stat.h>
#endif

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

void build_frontend() {
    printf("Checking if dist exists\n");

    #ifdef _WIN32
    struct stat st;
    if(stat("frontend\\dist", &st) != 0) {
        printf("Frontend dist not found. Building static files\n");

        system("cd frontend && npm run build");
    }
    #else
    struct stat st;
    if (stat("frontend/dist", &st) != 0) {
        printf("Frontend distnot found. Building static files\n");

        system("cd frontend && npm run build");
    }
    #endif

    printf("Static files built\n");
}

void setup_python_venv() {
    printf("Checking Python virtual environment\n");
    
    #ifdef _WIN32
    struct stat st;
    if (stat("backend\\venv", &st) != 0) {
        printf("Virtual environment not found. Creating venv\n");

        system("cd backend && python -m venv venv");
        
        printf("Virtual environment created\n");
    }
    printf("Installing/updating dependencies...\n");
    
    system("cd backend && call venv\\Scripts\\activate && pip install -r requirements.txt");
    
    #else
    struct stat st;
    if (stat("backend/venv", &st) != 0) {
        printf("Virtual environment not found. Creating venv\n");
        
        system("cd backend && python -m venv venv");

        printf("Virtual environment created\n");
    }
    printf("Installing/updating dependencies\n");
    
    system("cd backend && source venv/bin/activate && pip install -r requirements.txt");
    #endif
    
    printf("Python environment ready. Starting backend\n");
}

int main()
{
    char* dev_mode = getenv("DEV_MODE");

    webview_t w = webview_create(0, NULL);
    webview_set_title(w, "Buddy");
    webview_set_size(w, 600, 800, WEBVIEW_HINT_NONE);

    if(dev_mode && strcmp(dev_mode, "1") == 0) {
        webview_navigate(w, "http://localhost:5173");
    }
    else {
        // build static files if needed
        build_frontend();

        // Serve static files with http server
        #ifdef _WIN32
        system("start /B cmd /C \"cd frontend\\dist && python -m http.server 8080\"");
        Sleep(2000);
        #else
        system("cd frontend/dist && python3 -m http.server 8080 &");
        sleep(2);
        #endif
        webview_navigate(w, "http://localhost:8080");
    }

    // Set up venv if one doesn't exist
    setup_python_venv();

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
            setenv("GDK_BACKEND", "wayland", 1);
            execlp("bash", "bash", "-c", "cd backend && source venv/bin/activate && python3 main.py", NULL);

            perror("exec failed");
            exit(1);
        }

        // Parent process
        
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
