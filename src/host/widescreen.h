#ifndef BUFFY_WIDESCREEN_H
#define BUFFY_WIDESCREEN_H
#include "kernel/nv2a_hud_anchor.h"
int buffy_HudAnchor(const struct nv2a_hud_anchor_info *batch);
void buffy_ConfigureWidescreen(void);
float buffy_CullAspect(void);
#endif
