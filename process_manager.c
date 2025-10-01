#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>

#ifdef _WIN32
    #include <windows.h>
    #include <winsock2.h>
    #include <ws2tcpip.h>
    #include <direct.h>
    #include <sys/stat.h>
#else
    #include <unistd.h>
    #include <sys/stat.h>
    #include <sys/wait.h>
    #include <sys/socket.h>
    #include <netinet/in.h>
    #include <arpa/inet.h>
    #include <fcntl.h>
#endif

#include "process_manager.h"

// Global variables for cleanup
pid_t frontend_server_pid = 0;
pid_t audio_service_pid = 0;
pid_t python_backend_pid = 0;

void cleanup_servers() {
    printf("\nCleaning up servers...\n");
    
    #ifdef _WIN32
    // Windows cleanup, kill tracked processes and by port
    
    // Kill audio service
    if (audio_service_pid > 0) {
        printf("Stopping audio service (PID: %d)\n", audio_service_pid);
        char cmd[256];
        snprintf(cmd, sizeof(cmd), "taskkill /f /pid %d /t 2>nul", audio_service_pid);
        system(cmd);
        audio_service_pid = 0;
    }
    
    // Kill python backend (cmd wrapper might not propagate termination)
    if (python_backend_pid > 0) {
        printf("Stopping python backend (PID: %d)\n", python_backend_pid);
        char cmd[256];
        snprintf(cmd, sizeof(cmd), "taskkill /f /pid %d /t 2>nul", python_backend_pid);
        system(cmd);
        python_backend_pid = 0;
    }
    
    
    // Fallback: kill processes by port  
    system("for /f \"tokens=5\" %a in ('netstat -aon ^| find \":8081\"') do taskkill /f /pid %a 2>nul");
    char* dev_mode = getenv("DEV_MODE");
    if (!(dev_mode && strcmp(dev_mode, "1") == 0)) {
        system("for /f \"tokens=5\" %a in ('netstat -aon ^| find \":8080\"') do taskkill /f /pid %a 2>nul");
    }
    
    #else
    // Linux cleanup, terminate tracked PIDs
    
    // kill audio service process
    if (audio_service_pid > 0) {
        printf("Stopping audio service (PID: %d)\n", audio_service_pid);
        kill(audio_service_pid, SIGKILL);
        waitpid(audio_service_pid, NULL, 0);
        audio_service_pid = 0;
    }
    
    // kill frontend server (prod mode only, dev mode uses external server)
    char* dev_mode = getenv("DEV_MODE");
    if (!(dev_mode && strcmp(dev_mode, "1") == 0)) {
        if (frontend_server_pid > 0) {
            printf("Stopping frontend server (PID: %d)\n", frontend_server_pid);
            kill(frontend_server_pid, SIGKILL);
            waitpid(frontend_server_pid, NULL, 0);
            frontend_server_pid = 0;
        }
    }
    
    // kill python backend
    if (python_backend_pid > 0) {
        printf("Stopping python backend (PID: %d)\n", python_backend_pid);
        kill(python_backend_pid, SIGTERM);
        waitpid(python_backend_pid, NULL, 0);
        python_backend_pid = 0;
    }
    
    // Fallback: kill any remaining processes
    system("pkill -f 'python.*audio-service.*main.py' 2>/dev/null");
    system("pkill -f 'python.*backend.*main.py' 2>/dev/null");
    system("pkill -f 'python.*http.server.*8080' 2>/dev/null");
    
    
    printf("All processes cleaned up\n");
    #endif
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

int setup_python_venv_backend() {
    printf("Checking Backend Python virtual environment\n");

    #ifdef _WIN32
    struct stat st;
    if (stat("backend\\venv", &st) != 0) {
        printf("Virtual environment not found. Creating venv\n");

        int err = system("cd backend && python -m venv venv");
        if (err != 0) {
            printf("Failed to create virtual environment\n");
            return err;
        }
        printf("Virtual environment created\n");
    }
    printf("Installing/updating dependencies...\n");

    int pip_err = system("cd backend && call venv\\Scripts\\activate && pip install -r requirements.txt");
    if (pip_err != 0) {
        printf("Failed to install dependencies\n");
        return pip_err;
    }

    printf("Dependencies installed. Waiting for environment to stabilize...\n");
    Sleep(1000); // 1 second delay

    #else

    struct stat st;
    if (stat("backend/venv", &st) != 0) {
        printf("Virtual environment not found. Creating venv\n");

        int err = system("cd backend && python3 -m venv venv");
        if (err != 0) {
            printf("Failed to create virtual environment\n");
            return err;
        }

        printf("Virtual environment created\n");
    }
    printf("Installing/updating dependencies\n");

    int pip_err = system("cd backend && source venv/bin/activate && pip install -r requirements.txt");
    if (pip_err != 0) {
        printf("Failed to install dependencies\n");
        return pip_err;
    }

    printf("Dependencies installed. Waiting for environment to stabilize...\n");
    sleep(1); // 1 second delay
    #endif

    printf("Python environment ready. Starting backend\n");

    return 0;
}

int setup_python_venv_audio() {
    printf("Checking Audio Service Python virtual environment\n");

    #ifdef _WIN32
    struct stat st;
    if (stat("audio-service\\venv", &st) != 0) {
        printf("Audio service virtual environment not found. Creating venv\n");

        int err = system("cd audio-service && python -m venv venv");
        if (err != 0) {
            printf("Failed to create audio service virtual environment\n");
            return err;
        }
        printf("Audio service virtual environment created\n");
    }
    printf("Installing/updating audio service dependencies...\n");

    int pip_err = system("cd audio-service && call venv\\Scripts\\activate && pip install -r requirements.txt");
    if (pip_err != 0) {
        printf("Failed to install audio service dependencies\n");
        return pip_err;
    }

    printf("Audio service dependencies installed. Waiting for environment to stabilize...\n");
    Sleep(1000); // 1 second delay

    #else

    struct stat st;
    if (stat("audio-service/venv", &st) != 0) {
        printf("Audio service virtual environment not found. Creating venv\n");

        int err = system("cd audio-service && python3 -m venv venv");
        if (err != 0) {
            printf("Failed to create audio service virtual environment\n");
            return err;
        }
        
        printf("Audio service virtual environment created\n");
    }
    printf("Installing/updating audio service dependencies\n");

    int pip_err = system("cd audio-service && source venv/bin/activate && pip install -r requirements.txt");
    if (pip_err != 0) {
        printf("Failed to install audio service dependencies\n");
        return pip_err;
    }

    printf("Audio service dependencies installed. Waiting for environment to stabilize...\n");
    sleep(1); // 1 second delay
    #endif

    printf("Audio service Python environment ready\n");

    return 0;
}

