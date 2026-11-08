#include "nv2a_hud_anchor.h"
#include <assert.h>
#include <math.h>
#include <string.h>
#include <stdio.h>

static int side, calls;
static int select_side(const struct nv2a_hud_anchor_info *b)
{
    assert(b->texture_hash == 1);
    calls++;
    return side;
}

int main(void)
{
    struct nv2a_hud_anchor_info b = {1, 0, 15, 128, 32, 640, 480, 107, 1, 1, 0, 4, 1, 38.03125f, 166.03125f, 20.0f, 84.0f};
    unsigned n;
    nv2a_hud_anchor_set(NULL);
    assert(nv2a_hud_anchor_dx(&b) == 0);
    nv2a_hud_anchor_set(select_side);
    side = -1;
    assert(nv2a_hud_anchor_dx(&b) == -107);
    side = 1;
    assert(nv2a_hud_anchor_dx(&b) == 107);
    side = 2;
    assert(nv2a_hud_anchor_dx(&b) == 0);
    side = -1;
    calls = 0;
    b.pad = 0; assert(nv2a_hud_anchor_dx(&b) == 0); b.pad = 107;
    b.two_d = 0; assert(nv2a_hud_anchor_dx(&b) == 0); b.two_d = 1;
    b.place = 1; assert(nv2a_hud_anchor_dx(&b) == 0);
    b.place = 2; assert(nv2a_hud_anchor_dx(&b) == 0); b.place = 0;
    b.texture_hash = 0; assert(nv2a_hud_anchor_dx(&b) == 0); b.texture_hash = 1;
    b.scale = 0; assert(nv2a_hud_anchor_dx(&b) == 0);
    b.scale = 6; assert(nv2a_hud_anchor_dx(&b) == 0); b.scale = 1;
    b.pad = UINT32_MAX; assert(nv2a_hud_anchor_dx(&b) == 0); b.pad = 107;
    assert(nv2a_hud_anchor_dx(NULL) == 0 && calls == 0);

    /* Oracle: transform guest x via NDC back to pixels; translation must
     * equal exactly one pad at every scale, with unchanged sprite width. */
    b.scale = 5; assert(nv2a_hud_anchor_dx(&b) == -107); b.scale = 1;
    for (n = 1; n <= 5; n++) {
        int direction;
        for (direction = -1; direction <= 1; direction++) {
            int dx = 107 * direction;
            double width = 854.0 * n;
            float c4 = 214.0f / 854.0f - 1.0f;
            double x0 = ((2.0 * 29 / 854 + c4) + 1) * width / 2;
            double x1 = ((2.0 * 93 / 854 + c4) + 1) * width / 2;
            double moved0, moved1;
            uint32_t box[4] = {107*n, 3*n, 747*n, 477*n};
            uint32_t before[4]; memcpy(before, box, sizeof box);
            if (dx) c4 += nv2a_hud_anchor_delta(640, 107, dx);
            moved0 = ((2.0 * 29 / 854 + c4) + 1) * width / 2;
            moved1 = ((2.0 * 93 / 854 + c4) + 1) * width / 2;
            assert(fabs(moved0 - x0 - dx*(int)n) < 0.001);
            assert(fabs((moved1 - moved0) - (x1 - x0)) < 0.001);
            nv2a_hud_anchor_box(box, 640, 107, n, dx);
            assert(box[0] == (uint32_t)(107 + dx)*n);
            assert(box[2] == (uint32_t)(747 + dx)*n);
            assert(box[1] == before[1] && box[3] == before[3]);
            if (!dx) assert(!memcmp(box, before, sizeof box));
        }
        {
            uint32_t box[4] = {0, 10, 854*n, 20};
            nv2a_hud_anchor_box(box,640,107,n,-107);
            assert(box[0] == 0 && box[2] == 747*n);
            box[0]=0; box[2]=854*n;
            nv2a_hud_anchor_box(box,640,107,n,107);
            assert(box[0] == 107*n && box[2] == 854*n);
        }
    }
    nv2a_hud_anchor_set(NULL);
    assert(nv2a_hud_anchor_dx(&b) == 0);
    puts("HUD translation and clipping: passed");
    return 0;
}
