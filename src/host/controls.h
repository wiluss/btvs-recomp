#ifndef BUFFY_CONTROLS_H
#define BUFFY_CONTROLS_H
#include "input/host_pad.h"
/* Installed once before guest/input threads. No live mutable mapping. */
void buffy_ConfigureKeyboard(void);
/* Startup-only optional host overlay seam, after remapping/actions. */
void buffy_InputSetOverlay(xbox_input_pad_filter_fn filter);
int buffy_InputProfileValid(const char *text);
void buffy_FilterInput(DWORD port, const struct xbox_host_pad *host, XBOX_INPUT_STATE *state);
#endif
