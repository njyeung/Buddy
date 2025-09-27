#ifndef AUDIO_SERVICE_H
#define AUDIO_SERVICE_H

#ifdef _WIN32
    #include <windows.h>
#else
    #include <unistd.h>
#endif

int setup_audio_pipe(void);
int connect_audio_pipe(void);
void send_text_to_audio_service(const char* text);
char* extract_assistant_message(const char* json_line);
void cleanup_audio_pipe(void);

#endif