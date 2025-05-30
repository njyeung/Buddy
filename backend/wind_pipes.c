#include <windows.h>
#include <stdio.h>
#include <tchar.h>

int main()
{
    HANDLE hReadPipe, hWritePipe;
    SECURITY_ATTRIBUTES sa = { sizeof(SECURITY_ATTRIBUTES), NULL, TRUE }; // Allow handle inheritance
    PROCESS_INFORMATION pi;
    STARTUPINFO si = { sizeof(STARTUPINFO) };
    BOOL bSuccess;
    char buffer[128];
    DWORD dwRead, dwWritten;

    // Create the pipe
    if (!CreatePipe(&hReadPipe, &hWritePipe, &sa, 0)) {
        fprintf(stderr, "CreatePipe failed.\n");
        return 1;
    }

    // Set up STARTUPINFO to redirect stdin for the child.
    // Here, we simulate communication in the same process for simplicity.

    // Write to the pipe
    const char *msg = "Hello from parent process!";
    bSuccess = WriteFile(hWritePipe, msg, (DWORD)strlen(msg), &dwWritten, NULL);
    if (!bSuccess || dwWritten != strlen(msg)) {
        fprintf(stderr, "WriteFile failed.\n");
        return 1;
    }

    // Close the write handle to signal end of data
    CloseHandle(hWritePipe);

    // Read from the pipe
    bSuccess = ReadFile(hReadPipe, buffer, sizeof(buffer) - 1, &dwRead, NULL);
    if (!bSuccess || dwRead == 0) {
        fprintf(stderr, "ReadFile failed or no data read.\n");
        return 1;
    }

    // Null terminate and print
    buffer[dwRead] = '\0';
    printf("Child process received: %s\n", buffer);

    // Close the read handle
    CloseHandle(hReadPipe);

    return 0;
}
