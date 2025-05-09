#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <errno.h>

#define INT_STACK_MAGIC 'S'
#define INT_STACK_SET_SIZE _IOW(INT_STACK_MAGIC, 1, unsigned int)

#define DEVICE_PATH "/dev/int_stack"

void print_usage(void) {
    printf("Usage:\n");
    printf("  kernel_stack set-size <size>   - Set the stack size\n");
    printf("  kernel_stack push <value>      - Push a value onto the stack\n");
    printf("  kernel_stack pop               - Pop a value from the stack\n");
    printf("  kernel_stack unwind            - Pop and display all values\n");
}

int main(int argc, char *argv[]) {
    int fd, ret;
    
    if (argc < 2) {
        print_usage();
        return 1;
    }
    
    fd = open(DEVICE_PATH, O_RDWR);
    if (fd < 0) {
        perror("Failed to open device");
        return 1;
    }
    
	if (strcmp(argv[1], "set-size") == 0) {
		if (argc != 3) {
		    printf("ERROR: set-size command requires a size parameter\n");
		    close(fd);
		    return 1;
		}
		
		char *endptr;
		long int size_val = strtol(argv[2], &endptr, 10);
		if (*endptr != '\0' || size_val <= 0) {
		    printf("ERROR: size should be > 0\n");
		    close(fd);
		    return 1;
		}
		
		unsigned int size = (unsigned int)size_val;
		ret = ioctl(fd, INT_STACK_SET_SIZE, &size);
		if (ret < 0) {
		    perror("Failed to set stack size");
		    close(fd);
		    return 1;
		}
	}
	else if (strcmp(argv[1], "push") == 0) {
		if (argc != 3) {
		    printf("ERROR: push command requires a value parameter\n");
		    close(fd);
		    return 1;
		}
		
		int value = atoi(argv[2]);
		ret = write(fd, &value, sizeof(int));
		if (ret < 0) {
		    if (errno == ERANGE) {
		        printf("ERROR: stack is full\n");
		        close(fd);
		        return -ERANGE;
		    } else {
		        perror("Failed to push value");
		        close(fd);
		        return 1;
		    }
		}
	}
    else if (strcmp(argv[1], "pop") == 0) {
        int value;
        ret = read(fd, &value, sizeof(int));
        if (ret == 0) {
            printf("NULL\n");
        } else if (ret < 0) {
            perror("Failed to pop value");
            close(fd);
            return 1;
        } else {
            printf("%d\n", value);
        }
    } 
    else if (strcmp(argv[1], "unwind") == 0) {
        int values[1024];
        int count = 0;
        int value;

        while (1) {
            ret = read(fd, &value, sizeof(int));
            if (ret == 0) {
                break;
            } else if (ret < 0) {
                perror("Failed to pop value");
                close(fd);
                return 1;
            }
            
            values[count++] = value;
        }
        
        for (int i = 0; i < count; i++) {
            printf("%d%s", values[i], (i < count - 1) ? " " : "\n");
        }
    } 
    else {
        printf("Unknown command: %s\n", argv[1]);
        print_usage();
        close(fd);
        return 1;
    }
    
    close(fd);
    return 0;
}
