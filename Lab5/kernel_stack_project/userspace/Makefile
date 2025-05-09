CC=gcc
CFLAGS=-Wall -Wextra

all: kernel_stack

kernel_stack: kernel_stack.c
	$(CC) $(CFLAGS) -o kernel_stack kernel_stack.c

clean:
	rm -f kernel_stack
