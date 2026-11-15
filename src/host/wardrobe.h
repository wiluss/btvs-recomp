#ifndef BUFFY_WARDROBE_H
#define BUFFY_WARDROBE_H
#include "input/host_pad.h"
void buffy_ConfigureWardrobe(void);
void buffy_WardrobeInput(DWORD port, const struct xbox_host_pad *host, XBOX_INPUT_STATE *state);
int buffy_WardrobeEnabled(void);
unsigned *buffy_WardrobePreview(const char *path);
#endif
