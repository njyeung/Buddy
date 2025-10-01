#ifndef PROCESS_MANAGER_H
#define PROCESS_MANAGER_H

#ifdef _WIN32
    #include <windows.h>
#else
    #include <unistd.h>
    #include <sys/types.h>
#endif

extern pid_t frontend_server_pid;
extern pid_t audio_service_pid;
extern pid_t python_backend_pid;

int port_in_use(int port);
void cleanup_servers(void);
int build_frontend(void);
int setup_python_venv_backend(void);
int setup_python_venv_audio(void);

#endif