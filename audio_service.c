#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifdef _WIN32
    #include <windows.h>
#else
    #include <unistd.h>
    #include <sys/stat.h>
    #include <fcntl.h>
#endif

#include "audio_service.h"
#include "process_manager.h"

int setup_audio_pipe(void) {
    #ifdef _WIN32
    printf("Setting up Windows audio pipe...\n");
    audio_pipe = CreateNamedPipe(
        "\\\\.\\pipe\\buddy_to_audio",
        PIPE_ACCESS_OUTBOUND,
        PIPE_TYPE_MESSAGE | PIPE_READMODE_MESSAGE | PIPE_WAIT,
        1,
        4096,
        4096,
        0,
        NULL
    );
    if (audio_pipe == INVALID_HANDLE_VALUE) {
        printf("Failed to create Windows audio pipe\n");
        return -1;
    }
    printf("Windows audio pipe created\n");
    #else
    printf("Setting up audio pipe...\n");
    if (mkfifo("/tmp/buddy_to_audio", 0666) != 0) {
        // Pipe might already exist, try to remove and recreate
        unlink("/tmp/buddy_to_audio");
        if (mkfifo("/tmp/buddy_to_audio", 0666) != 0) {
            printf("Failed to create audio pipe\n");
            return -1;
        }
    }
    printf("Audio pipe created\n");
    #endif
    
    return 0;
}

int connect_audio_pipe(void) {
    #ifdef _WIN32
    printf("Waiting for audio service to connect to Windows pipe...\n");
    if (!ConnectNamedPipe(audio_pipe, NULL)) {
        if (GetLastError() != ERROR_PIPE_CONNECTED) {
            printf("Failed to connect Windows audio pipe\n");
            return -1;
        }
    }
    printf("Windows audio pipe ready for communication\n");
    #else
    printf("Waiting for audio service to connect to pipe...\n");
    audio_write_fd = open("/tmp/buddy_to_audio", O_WRONLY);
    if (audio_write_fd == -1) {
        printf("Failed to open audio pipe for writing\n");
        return -1;
    }
    printf("Audio pipe ready for communication\n");
    #endif
    
    return 0;
}

void send_text_to_audio_service(const char* text) {
    #ifdef _WIN32
    if (audio_pipe == INVALID_HANDLE_VALUE) return;
    
    // Send simple command: "TTS:text\n"
    char msg[4096];
    snprintf(msg, sizeof(msg), "TTS:%s\n", text);
    
    DWORD written;
    if (!WriteFile(audio_pipe, msg, strlen(msg), &written, NULL)) {
        printf("Failed to send to audio service\n");
    }
    #else
    if (audio_write_fd == -1) return;
    
    // Send simple command: "TTS:text\n"
    char msg[4096];
    snprintf(msg, sizeof(msg), "TTS:%s\n", text);
    
    ssize_t written = write(audio_write_fd, msg, strlen(msg));
    if (written == -1) {
        printf("Failed to send to audio service\n");
    }
    #endif
}

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

void cleanup_audio_pipe(void) {
    #ifdef _WIN32
    if (audio_pipe != INVALID_HANDLE_VALUE) {
        CloseHandle(audio_pipe);
        audio_pipe = INVALID_HANDLE_VALUE;
    }
    #else
    if (audio_write_fd != -1) {
        close(audio_write_fd);
        audio_write_fd = -1;
    }
    unlink("/tmp/buddy_to_audio");
    #endif
}