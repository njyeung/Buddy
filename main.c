#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>
#include <webview/webview.h>
#include "process_manager.h"
#include "audio_service.h"

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
    #include <fcntl.h>
#endif

char* dev_mode = NULL;


void signal_handler(int sig) {
    printf("\nShutting down gracefully...\n");
    cleanup_servers();
    exit(0);
}

#ifdef _WIN32
typedef struct{
    HANDLE stdinWrite;
    HANDLE stdoutRead;
    webview_t w;
} PipeHandles;
#else
typedef struct {
    int stdinWrite;
    int stdoutRead;
    webview_t w;
} PipeHandles;
#endif

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


// On data from Python backend 
static void output(webview_t w, void *arg)
{
    const char *msg = (const char *)arg;
    size_t len = strlen(msg);
    if (len > 0 && msg[len - 1] == '\n')
    {
        ((char *)msg)[len - 1] = '\0';
    }
    char js[32768];
    // forward backend message to frontend
    snprintf(js, sizeof(js), "receiveData(%s);", msg);
    webview_eval(w, js);
    free(arg);
}
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
                
                // Check if it is a log message, CONTINUE if it is
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
                
                // Finally, dispatch to frontend
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

        // Growing buffer to store incomplete data
        size_t bufferSize = 1024;
        char *buffer = malloc(bufferSize);

        // Current amount of data in buffer
        size_t bufferLen = 0;
        if (!buffer) return NULL;

        // Chunk array for fetching new data
        char chunk[1024];
        ssize_t bytesRead;

        while (1) {
            // Read python stdout into chunk and null terminate
            bytesRead = read(p->stdoutRead, chunk, sizeof(chunk) - 1);
            if (bytesRead <= 0) break;
            chunk[bytesRead] = '\0';
            
            // There are 2 scenarios:
            //  a. >=1 complete lines were read
            //  b. 0 complete lines were read
            // In both scenarios, it's possible that there is an incomplete line at the end
            
            // Grow buffer if needed
            // This happens with the b scenario. 
            // If we have a really long string:
            //  -> multiple iterations of the while loop
            //  -> multiple chunks were read without a newline character.
            if (bufferLen + bytesRead + 1 >= bufferSize) {
                bufferSize = (bufferLen + bytesRead + 1) * 2;
                buffer = realloc(buffer, bufferSize);
            }

            // Add chunk to end of buffer
            memcpy(buffer + bufferLen, chunk, bytesRead);
            bufferLen += bytesRead;
            buffer[bufferLen] = '\0';

            // process complete lines
            char *lineStart = buffer;
            char *newline;
            // This is scenario a
            // While there are complete lines, we can keep consuming them 
            while ((newline = strchr(lineStart, '\n')) != NULL) {
                *newline = '\0';

                // Check if it is a log message, CONTINUE if it is
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
                
                // Finally, dispatch to frontend
                webview_dispatch(w, output, strdup(lineStart));

                // Move to the start of the next line
                lineStart = newline + 1;
            }

            // This can be both scenario a and b, there is a partial line leftover
            // Save leftover data and move it to the beginning of the buffer
            //      This doesn't do anything for scenario b
            size_t leftover = buffer + bufferLen - lineStart;
            memmove(buffer, lineStart, leftover);
            bufferLen = leftover;
        }

        free(buffer);
        return NULL;
    }
#endif


int main()
{
    // signal handlers -> cleanup child processes
    signal(SIGINT, signal_handler);     // Ctrl+C
    signal(SIGTERM, signal_handler);    // Termination
    #ifndef _WIN32
    signal(SIGHUP, signal_handler);     // Terminal hangup
    #endif
    

    // for development frontend server (npm run dev)
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
    
    // Setup audio pipe
    if (setup_audio_pipe() != 0) {
        printf("Failed to setup audio pipe\n");
        exit(1);
    }

    // Start audio service
    if (start_audio_service() != 0) {
        printf("could not start audio service\n");
        exit(1);
    }

    // Connect to audio pipe
    if (connect_audio_pipe() != 0) {
        printf("Failed to connect to audio pipe\n");
        exit(1);
    }


    // Linux stuff :/
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
        
        frontend_server_pid = fork();
        if (frontend_server_pid == 0) {
            // Child process
            chdir("frontend/dist");
            execlp("python3", "python3", "-m", "http.server", "8080", "--bind", "127.0.0.1", NULL);
            perror("exec failed for frontend server");
            exit(1);
        } else if (frontend_server_pid < 0) {
            perror("Fork failed for frontend server");
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
        
        // Store backend PID for cleanup
        python_backend_pid = pi.dwProcessId;

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

    cleanup_servers();

    #ifdef _WIN32
        CloseHandle(pipeHandles.stdinWrite);
        CloseHandle(pipeHandles.stdoutRead);
        CloseHandle(pi.hProcess);
        CloseHandle(pi.hThread);
    #else
        close(pipeHandles.stdinWrite);
        close(pipeHandles.stdoutRead);
    #endif

    exit(0);
}
