#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "audio_service.h"

// Audio service communication is now handled directly via native pipes in main.c
// These functions are kept for compatibility but are no longer used

int setup_audio_pipe(void) {
    // No longer needed - pipes are set up directly in main.c
    return 0;
}

int connect_audio_pipe(void) {
    // No longer needed - pipes are connected directly in main.c
    return 0;
}

void send_json_to_audio_service(const char* json) {
    // No longer needed - messages are sent directly via pipes in main.c
    // This function remains for compatibility but does nothing
}

void cleanup_audio_pipe(void) {
    // No longer needed - pipes are cleaned up directly in main.c
}