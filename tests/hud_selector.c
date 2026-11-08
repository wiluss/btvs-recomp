#define _POSIX_C_SOURCE 200809L
#include "widescreen.h"
#include <assert.h>
#include <stdlib.h>
#include <math.h>

static void changing_gauges(void)
{
    static const uint64_t bars[] = {
        UINT64_C(0x5C0AEC067A11F3CA), UINT64_C(0x8A6D546A37DDE7B2),
        UINT64_C(0x4850AF87563CAB06), UINT64_C(0xFA55C2FCB5B19796),
        UINT64_C(0xBDA16A353D47A3C5), UINT64_C(0x03BFE66B13F8D20A),
    };
    static const uint32_t programs[] = {0x969115CFu, 0xC8AF571Fu};
    struct nv2a_hud_anchor_info b = {
        0, 0, 15, 256, 32, 640, 480, 107, 4, 1, 0, 4, 1,
        0, 0, 41.03125f, 73.03125f
    };
    /* Full normal gauge span: zero to maximum, including the old 240 cutoff.
     * Frames, fills and glow must all keep the same translation on both VPs. */
    for (unsigned p = 0; p < 2; p++) {
        b.program_hash = programs[p];
        for (unsigned i = 0; i < sizeof bars / sizeof bars[0]; i++) {
            b.texture_hash = bars[i];
            for (unsigned step = 1; step <= 2440; step++) {
                float extent = step * 0.1f;
                b.lo_x = 74.03125f; b.hi_x = b.lo_x + extent;
                assert(buffy_HudAnchor(&b) == -1);
                b.hi_x = 572.03125f; b.lo_x = b.hi_x - extent;
                assert(buffy_HudAnchor(&b) == 1);
            }
            b.lo_x = b.hi_x = 74.03125f; assert(!buffy_HudAnchor(&b));
            b.lo_x = 74.03125f; b.hi_x = 620; assert(!buffy_HudAnchor(&b));
        }
    }
    b.texture_hash = UINT64_C(0x05022C9E2BA4B93F);
    b.texture_width = b.texture_height = 64;
    b.lo_x = 546.03125f; b.hi_x = 610.03125f;
    b.lo_y = 29.03125f; b.hi_y = 93.03125f;
    assert(buffy_HudAnchor(&b) == 1);
    b.texture_hash = UINT64_C(0x696883C210FA85C1); assert(buffy_HudAnchor(&b) == 1);
    b.texture_hash = UINT64_C(0x43C5401E18797246);
    b.texture_width = b.texture_height = 32;
    b.lo_x = 562.03125f; b.hi_x = 594.03125f;
    b.lo_y = 40.03125f; b.hi_y = 72.03125f;
    assert(buffy_HudAnchor(&b) == 1);
    b.texture_hash = UINT64_C(0x9C8D2432C0EB962D); assert(buffy_HudAnchor(&b) == 1);
    b.texture_hash = UINT64_C(0x9DA02D33F53C9751);
    b.texture_width = 128; b.texture_height = 32;
    b.lo_x = 450; b.hi_x = 578; assert(buffy_HudAnchor(&b) == 1);
    b.lo_x = 38; b.hi_x = 166; assert(!buffy_HudAnchor(&b));
    b.texture_hash = UINT64_C(0x6B4E9AA9BC99D931);
    b.texture_width = b.texture_height = 32;
    b.lo_x = 45.03125f; b.hi_x = 77.03125f;
    assert(buffy_HudAnchor(&b) == -1);
    b.lo_x = 562; b.hi_x = 594; assert(!buffy_HudAnchor(&b));
    /* Dialogue caps are shared menu art, never health-bar sprites. */
    b.texture_hash = UINT64_C(0x414D1E1F4A351779); b.texture_height = 64;
    b.lo_x = 38; b.hi_x = 70; assert(!buffy_HudAnchor(&b));
}

int main(void)
{
    changing_gauges();
    struct nv2a_hud_anchor_info b = {
        UINT64_C(0x1D03BB8D6EC30520), 0x969115CFu, 15, 128, 32, 640, 480, 107, 4, 1, 0, 4, 1, 38.03125f, 166.03125f, 20.0f, 84.0f
    };
    assert(buffy_HudAnchor(&b) == -1);
    b.bounds_valid = 0; assert(!buffy_HudAnchor(&b)); b.bounds_valid = 1;
    b.lo_y = 380; b.hi_y = 420; assert(!buffy_HudAnchor(&b));
    b.lo_y = 20; b.hi_y = 84;
    b.hi_y = NAN; assert(!buffy_HudAnchor(&b)); b.hi_y = 84;
    /* Reused texture on a wide tutorial panel must not move its background. */
    b.hi_x = 620; assert(!buffy_HudAnchor(&b)); b.hi_x = 166.03125f;
    b.lo_x = -20; assert(!buffy_HudAnchor(&b)); b.lo_x = 38.03125f;
    b.lo_x = NAN; assert(!buffy_HudAnchor(&b)); b.lo_x = 38.03125f;
    b.hi_x = NAN; assert(!buffy_HudAnchor(&b)); b.hi_x = 166.03125f;
    b.vertex_count = 8; assert(!buffy_HudAnchor(&b)); b.vertex_count = 4;
    b.texture_hash ^= 1; assert(!buffy_HudAnchor(&b)); b.texture_hash ^= 1;
    b.texture_width++; assert(!buffy_HudAnchor(&b)); b.texture_width--;
    b.texture_height++; assert(!buffy_HudAnchor(&b)); b.texture_height--;
    /* Captured combo quad: retain its offset from the already anchored bars. */
    b.texture_hash = UINT64_C(0x488AE9014900B714);
    b.texture_width = b.texture_height = 16;
    b.lo_x = 72.03125f; b.hi_x = 88.03125f;
    b.lo_y = 35.0972f; b.hi_y = 45.03125f;
    assert(buffy_HudAnchor(&b) == -1);
    b.texture_hash = UINT64_C(0x2E63C213DFAECEFC); b.texture_height = 32;
    assert(buffy_HudAnchor(&b) == -1);
    b.texture_hash = UINT64_C(0xAC3F79F465473250);
    assert(buffy_HudAnchor(&b) == -1);
    b.lo_x = 500; b.hi_x = 516; assert(!buffy_HudAnchor(&b));
    b.lo_y = 380; b.hi_y = 412; assert(!buffy_HudAnchor(&b));
    b.texture_hash = UINT64_C(0x1D03BB8D6EC30520);
    b.texture_width = 128; b.texture_height = 32;
    b.lo_x = 38.03125f; b.hi_x = 166.03125f; b.lo_y = 20; b.hi_y = 84;
    b.format = 12; assert(!buffy_HudAnchor(&b)); b.format = 15;
    b.program_hash++; assert(!buffy_HudAnchor(&b)); b.program_hash--;
    b.width = 320; assert(!buffy_HudAnchor(&b)); b.width = 640;
    b.height = 240; assert(!buffy_HudAnchor(&b)); b.height = 480;
    b.two_d = 0; assert(!buffy_HudAnchor(&b)); b.two_d = 1;
    b.place = 1; assert(!buffy_HudAnchor(&b)); b.place = 0;
    /* The shared text atlas from the same scene must remain centred. */
    b.texture_hash = UINT64_C(0x2D68EC4C7053FC43);
    b.texture_width = 128; b.texture_height = 256;
    assert(!buffy_HudAnchor(&b));
    b.texture_hash = UINT64_C(0x1D03BB8D6EC30520); b.texture_height = 32;
    unsetenv("BUFFY_HUD"); buffy_ConfigureWidescreen();
    assert(!nv2a_hud_anchor_dx(&b));
    setenv("BUFFY_HUD", "edges", 1); buffy_ConfigureWidescreen();
    assert(nv2a_hud_anchor_dx(&b) == -107);
    struct nv2a_hud_anchor_info player = b;
    b.texture_hash = UINT64_C(0x43C5401E18797246);
    b.texture_width = b.texture_height = 32;
    b.lo_x = 562.03125f; b.hi_x = 594.03125f;
    b.lo_y = 40.03125f; b.hi_y = 72.03125f;
    assert(nv2a_hud_anchor_dx(&b) == 107);
    b = player;
    b.pad = 0; assert(!nv2a_hud_anchor_dx(&b)); b.pad = 107;
    setenv("BUFFY_HUD", "safe", 1); buffy_ConfigureWidescreen();
    assert(!nv2a_hud_anchor_dx(&b));
    setenv("BUFFY_HUD", "unknown", 1); buffy_ConfigureWidescreen();
    assert(!nv2a_hud_anchor_dx(&b));
    return 0;
}
