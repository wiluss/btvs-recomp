#include "widescreen.h"
#include <stdlib.h>
#include <string.h>

/* Content identities from this project's own captures, not guest addresses.
 * XBE cd49da614d92b6ec94f3bd66d503eb4e214f8809e9c7b42f465ee25c709ad35f.
 * Identified player/enemy HUD sprites move to their respective edges.
 * Shared bars use the original screen half, not a cutoff on their changing
 * filled extent. Wide tutorial panels span the centre and remain centred.
 * See docs/BRINGUP.md and docs/PROVENANCE.md for measurements and limits. */
struct hud_sprite { uint64_t hash; uint32_t width, height; };
static float s_cull_aspect = 1.0f;

float buffy_CullAspect(void)
{
    return s_cull_aspect;
}
static const struct hud_sprite s_player[] = {
    {UINT64_C(0x1D03BB8D6EC30520), 128, 32},
    {UINT64_C(0xA42E5E8EBEDB38C7), 64, 64},
    {UINT64_C(0x7298C201390FA420), 64, 64},
    {UINT64_C(0xDC095DC8CAAA131D), 32, 32},
    {UINT64_C(0x6B4E9AA9BC99D931), 32, 32},
    /* IComboDisplay shares the player's upper-left HUD, not the world view. */
    {UINT64_C(0x488AE9014900B714), 16, 16},
    {UINT64_C(0x2E63C213DFAECEFC), 16, 32},
    {UINT64_C(0xAC3F79F465473250), 16, 32},
};

static const struct hud_sprite s_enemy[] = {
    {UINT64_C(0x9DA02D33F53C9751), 128, 32},
    {UINT64_C(0x43C5401E18797246), 32, 32},
    {UINT64_C(0x9C8D2432C0EB962D), 32, 32},
    {UINT64_C(0x05022C9E2BA4B93F), 64, 64},
    {UINT64_C(0x696883C210FA85C1), 64, 64},
};

static const struct hud_sprite s_bars[] = {
    {UINT64_C(0x5C0AEC067A11F3CA), 256, 32},
    {UINT64_C(0x8A6D546A37DDE7B2), 256, 32},
    {UINT64_C(0x4850AF87563CAB06), 256, 32},
    {UINT64_C(0xFA55C2FCB5B19796), 256, 32},
    {UINT64_C(0xBDA16A353D47A3C5), 256, 32},
    {UINT64_C(0x03BFE66B13F8D20A), 256, 32},
};

static int matches(const struct nv2a_hud_anchor_info *b,
                   const struct hud_sprite *sprites, size_t count)
{
    for (size_t i = 0; i < count; i++)
        if (b->texture_hash == sprites[i].hash && b->texture_width == sprites[i].width
            && b->texture_height == sprites[i].height)
            return 1;
    return 0;
}

int buffy_HudAnchor(const struct nv2a_hud_anchor_info *b)
{
    int side;
    if (!b || !b->two_d || b->place || b->width != 640 || b->height != 480
        || b->vertex_count != 4 || !b->bounds_valid
        || !(b->lo_y >= 0.0f && b->hi_y <= 100.0f && b->hi_y > b->lo_y)
        || !(b->lo_x >= 0.0f && b->hi_x <= 640.0f && b->hi_x > b->lo_x)
        || !b->pad || (b->program_hash != 0x969115CFu && b->program_hash != 0xC8AF571Fu)
        || b->format != 0xFu)
        return 0;
    side = b->hi_x < 320.0f ? -1 : b->lo_x > 320.0f ? 1 : 0;
    if (side && matches(b, s_bars, sizeof s_bars / sizeof s_bars[0]))
        return side;
    if (side == -1 && matches(b, s_player, sizeof s_player / sizeof s_player[0]))
        return -1;
    if (side == 1 && matches(b, s_enemy, sizeof s_enemy / sizeof s_enemy[0]))
        return 1;
    return 0;
}

void buffy_ConfigureWidescreen(void)
{
    const char *mode = getenv("BUFFY_HUD");
    const char *wide = getenv("BUFFY_WIDESCREEN");
    const char *cull = getenv("BUFFY_WIDE_CULL");
    s_cull_aspect = wide && !strcmp(wide, "1") && !(cull && !strcmp(cull, "0"))
                    ? 854.0f / 640.0f : 1.0f;
    nv2a_hud_anchor_set(mode && !strcmp(mode, "edges") ? buffy_HudAnchor : NULL);
}
