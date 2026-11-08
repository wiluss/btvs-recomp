#include <stdio.h>
#include <unistd.h>

int main(void) {
    const long page_size = sysconf(_SC_PAGESIZE);
    if (page_size <= 0) {
        fputs("Unable to query the host page size.\n", stderr);
        return 1;
    }
#if defined(__aarch64__) || defined(__arm64__)
    const char *arch = "arm64";
#elif defined(__x86_64__)
    const char *arch = "x86_64";
#else
    const char *arch = "other";
#endif
    printf("{\"diagnostic\":\"host_only\",\"architecture\":\"%s\","
           "\"pointer_bits\":%zu,\"host_page_bytes\":%ld,"
           "\"game_started\":false}\n", arch, sizeof(void *) * 8, page_size);
    return 0;
}
