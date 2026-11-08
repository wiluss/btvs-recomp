#include <stdlib.h>
#include <string.h>

int buffy_ArenasEnabled(void)
{
    const char *value = getenv("BUFFY_UNLOCK_ARENAS");
    return value && strcmp(value, "1") == 0;
}
