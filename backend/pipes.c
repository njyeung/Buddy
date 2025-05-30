#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>

int main() {
    int pipefd[2];
    pid_t cpid;
    char buf;

    // Create the pipe
    if (pipe(pipefd) == -1) {
        perror("pipe");
        exit(EXIT_FAILURE);
    }

    // Fork the process
    cpid = fork();
    if (cpid == -1) {
        perror("fork");
        exit(EXIT_FAILURE);
    }

    if (cpid == 0) {    // Child process
        close(pipefd[1]);          // Close unused write end

        // Read from pipe and output to stdout
        while (read(pipefd[0], &buf, 1) > 0) {
            write(STDOUT_FILENO, &buf, 1);
        }
        write(STDOUT_FILENO, "\n", 1);
        close(pipefd[0]);
        _exit(EXIT_SUCCESS);

    } else {            // Parent process
        close(pipefd[0]);          // Close unused read end
        char *msg = "Hello from parent";

        // Write message to pipe
        write(pipefd[1], msg, strlen(msg));
        close(pipefd[1]);          // Reader will see EOF

        wait(NULL);                // Wait for child to finish
        exit(EXIT_SUCCESS);
    }
}
