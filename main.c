#include <windows.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#define WEBVIEW_WINAPI
#include "webview/webview.h"

// Convert UTF-8 char* to wide wchar_t* and print it
void print_utf8(const char* utf8) {
    HANDLE hConsole = GetStdHandle(STD_OUTPUT_HANDLE);

    // Convert UTF-8 to UTF-16 (wide char)
    int wlen = MultiByteToWideChar(CP_UTF8, 0, utf8, -1, NULL, 0);
    wchar_t* wstr = (wchar_t*)malloc(wlen * sizeof(wchar_t));
    if (!wstr) return;

    MultiByteToWideChar(CP_UTF8, 0, utf8, -1, wstr, wlen);

    // Write to console
    DWORD written;
    WriteConsoleW(hConsole, wstr, wlen - 1, &written, NULL);

    free(wstr);
}

typedef struct {
    HANDLE stdinWrite;
    HANDLE stdoutRead;
    webview_t w;
} PipeHandles;

static void producer(const char* seq, const char *req, void *arg) {
    PipeHandles* pipes = (PipeHandles *)arg;

    // Send it to Python
    webview_t w = pipes->w;
    char js[1024];

    // Forward to Python via stdin pipe
    DWORD written;
    WriteFile(pipes->stdinWrite, req, strlen(req), &written, NULL);
    WriteFile(pipes->stdinWrite, "\n", 1, &written, NULL);
}

static void output(webview_t w, void *arg) {
    const char *msg = (const char *)arg;

    // Trim trailing newline
    size_t len = strlen(msg);
    if (len > 0 && msg[len - 1] == '\n') {
        ((char *)msg)[len - 1] = '\0';
    }
    
    char js[32768];
    snprintf(js, sizeof(js), "receiveData(%s);", msg);

    webview_eval(w, js);

    free(arg); 
}

// Consumer thread: reads from Python and pipes to frontend
DWORD WINAPI consumer_thread(LPVOID lpParam) {
    PipeHandles *p = (PipeHandles *)lpParam;
    HANDLE hStdoutRead = p->stdoutRead;
    webview_t w = p->w;
    
    
    size_t bufferSize = 1024;
    char *buffer = malloc(bufferSize);
    size_t bufferLen = 0;

    if(!buffer) {
        fprintf(stderr, "malloc failed");
        return 1;
    }
    
    char chunk[1024];
    DWORD bytesRead;

    while (1) {
        if (!ReadFile(hStdoutRead, chunk, sizeof(chunk) - 1, &bytesRead, NULL)) {
            fprintf(stderr, "Failed to read from Python stdout.\n");
            break;
        }

        chunk[bytesRead] = '\0';

        // Append chunk to buffer
        if (bufferLen + bytesRead + 1 >= bufferSize) {
            size_t newSize = (bufferLen + bytesRead + 1) * 2;
            char *newBuffer = realloc(buffer, newSize);
            if (!newBuffer) {
                fprintf(stderr, "Failed to allocate memory!\n");
                free(buffer);
                break;
            }
            buffer = newBuffer;
            bufferSize = newSize;
        }

        memcpy(buffer + bufferLen, chunk, bytesRead);
        bufferLen += bytesRead;
        buffer[bufferLen] = '\0';

        // Extract complete lines
        char *lineStart = buffer;
        char *newline;
        while ((newline = strchr(lineStart, '\n')) != NULL) {
            *newline = '\0';

            const char *logPrefix = "{\"type\": \"log\"";
            if (strncmp(lineStart, logPrefix, strlen(logPrefix)) == 0) {
                printf("[LOG] %s\n", lineStart);
                lineStart = newline + 1;
                continue;
            }
            

            webview_dispatch(w, output, _strdup(lineStart));
            lineStart = newline + 1;
        }

        // Move leftover partial line to front of buffer
        size_t leftover = buffer + bufferLen - lineStart;
        memmove(buffer, lineStart, leftover);
        bufferLen = leftover;
    }

    free(buffer);
    return 0;
}


int main() {
    webview_t w = webview_create(0, NULL);
    webview_set_title(w, "Buddy");
    webview_set_size(w, 600, 800, WEBVIEW_HINT_NONE);
    webview_navigate(w, "http://localhost:5173");
    

    SECURITY_ATTRIBUTES sa = { sizeof(SECURITY_ATTRIBUTES), NULL, TRUE };

    HANDLE hChildStdoutRd, hChildStdoutWr;
    HANDLE hChildStdinRd, hChildStdinWr;

    // Create pipes for child's stdout
    CreatePipe(&hChildStdoutRd, &hChildStdoutWr, &sa, 0);
    SetHandleInformation(hChildStdoutRd, HANDLE_FLAG_INHERIT, 0);

    // Create pipes for child's stdin
    CreatePipe(&hChildStdinRd, &hChildStdinWr, &sa, 0);
    SetHandleInformation(hChildStdinWr, HANDLE_FLAG_INHERIT, 0);

    // Set up child's startup info
    STARTUPINFO si = { sizeof(si) };
    PROCESS_INFORMATION pi;

    si.dwFlags = STARTF_USESTDHANDLES;
    si.hStdOutput = hChildStdoutWr;
    si.hStdInput = hChildStdinRd;
    si.hStdError = GetStdHandle(STD_ERROR_HANDLE);

    char cmd[] = "python .\\backend\\main.py";

    // Create child process
    if (!CreateProcess(NULL, cmd, NULL, NULL, TRUE, 0, NULL, NULL, &si, &pi)) {
        fprintf(stderr, "CreateProcess failed: %lu\n", GetLastError());
        return 1;
    }

    // Parent doesn’t use these
    CloseHandle(hChildStdoutWr);
    CloseHandle(hChildStdinRd);

    PipeHandles pipeHandles = { hChildStdinWr, hChildStdoutRd, w };
    
    // Create consumer thread
    CreateThread(NULL, 0, consumer_thread, &pipeHandles, 0, NULL);
    // Bind consumer thread
    webview_bind(w, "invoke", producer, &pipeHandles);

    webview_run(w);
    webview_destroy(w);

    // Cleanup
    CloseHandle(hChildStdinWr);
    CloseHandle(hChildStdoutRd);
    CloseHandle(pi.hProcess);
    CloseHandle(pi.hThread);

    return 0;
}