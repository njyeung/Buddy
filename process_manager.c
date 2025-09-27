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

// Audio service pipe handles
#ifdef _WIN32
HANDLE audio_pipe = INVALID_HANDLE_VALUE;
#else
int audio_write_fd = -1;
#endif

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
    
    // Close Windows audio pipe
    if (audio_pipe != INVALID_HANDLE_VALUE) {
        CloseHandle(audio_pipe);
        audio_pipe = INVALID_HANDLE_VALUE;
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
    
    // Close audio pipe
    if (audio_write_fd != -1) {
        close(audio_write_fd);
        audio_write_fd = -1;
    }
    
    // Clean up named pipe
    unlink("/tmp/buddy_to_audio");
    
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

int setup_python_venv() {
    printf("Checking Python virtual environment\n");

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
    
    // Use CreateProcess to track audio service PID
    STARTUPINFO si_audio = {sizeof(si_audio)};
    PROCESS_INFORMATION pi_audio;
    char audio_cmd[] = "cmd /C \"cd audio-service && call venv\\Scripts\\activate && python main.py\"";
    
    if (!CreateProcess(NULL, audio_cmd, NULL, NULL, FALSE, CREATE_NEW_CONSOLE, NULL, NULL, &si_audio, &pi_audio)) {
        fprintf(stderr, "CreateProcess failed for audio service: %lu\n", GetLastError());
        exit(1);
    }
    
    // Store audio service PID for cleanup
    audio_service_pid = pi_audio.dwProcessId;
    
    // Close handles we don't need
    CloseHandle(pi_audio.hProcess);
    CloseHandle(pi_audio.hThread);
    
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
    
    // Create pipe to capture audio service output
    int pipefd[2];
    if (pipe(pipefd) == -1) {
        perror("Failed to create pipe for audio service");
        exit(1);
    }
    
    audio_service_pid = fork();
    if (audio_service_pid == 0) {
        // Child process
        close(pipefd[0]); // Close read end
        dup2(pipefd[1], STDOUT_FILENO); // Redirect stdout to pipe
        dup2(pipefd[1], STDERR_FILENO); // Redirect stderr to pipe
        close(pipefd[1]);
        
        chdir("audio-service");
        execlp("bash", "bash", "-c", "source venv/bin/activate && python3 main.py", NULL);
        perror("exec failed for audio service");
        exit(1);
    } else if (audio_service_pid < 0) {
        perror("Fork failed for audio service");
        exit(1);
    }
    
    // Parent process - wait for "AUDIO_SERVICE_READY" message
    close(pipefd[1]); // Close write end
    
    FILE *audio_output = fdopen(pipefd[0], "r");
    if (!audio_output) {
        perror("Failed to open audio service output stream");
        exit(1);
    }
    
    printf("Waiting for audio service to initialize...\n");
    char line[1024];
    int ready = 0;
    
    while (fgets(line, sizeof(line), audio_output)) {
        printf("[AUDIO] %s", line); // Forward audio service logs
        
        if (strstr(line, "AUDIO_SERVICE_READY")) {
            ready = 1;
            break;
        }
        
        if (strstr(line, "AUDIO_SERVICE_FAILED")) {
            printf("Audio service initialization failed\n");
            fclose(audio_output);
            exit(1);
        }
    }
    
    fclose(audio_output);
    
    if (!ready) {
        printf("Audio service failed to start properly\n");
        exit(1);
    }
    #endif
    
    printf("Audio service started on port 8081\n");
    return 0;
}