#include <stdio.h>
#include <math.h>
#include <float.h>
#include "nv2a_screen_w.h"

static int test_count = 0, pass_count = 0;
#define CHECK(cond, msg) do { test_count++; if (cond) pass_count++; else printf("FAIL: %s\n", msg); } while(0)

int main(void) {
    float w;

    /* ±0 */
    CHECK(nv2a_screen_w(0.0f) == 1.0f, "+0 -> 1");
    CHECK(nv2a_screen_w(-0.0f) == 1.0f, "-0 -> 1");

    /* ±inf */
    w = nv2a_screen_w(INFINITY);
    CHECK(w == 0x1p64f, "+inf -> +2^64");
    w = nv2a_screen_w(-INFINITY);
    CHECK(w == -0x1p64f, "-inf -> -2^64");

    /* NaN */
    w = nv2a_screen_w(NAN);
    CHECK(isnan(w), "NaN preserved");

    /* Normaux & bornes */
    CHECK(nv2a_screen_w(2.0f) == 2.0f, "w=2 unchanged");
    CHECK(nv2a_screen_w(-4.0f) == -4.0f, "w=-4 unchanged");
    CHECK(nv2a_screen_w(FLT_MAX) == FLT_MAX, "FLT_MAX preserved");
    CHECK(nv2a_screen_w(FLT_MIN) == FLT_MIN, "FLT_MIN preserved");

    /* Quad synthétique (posXYZ finis déjà divisés) & perspective */
    CHECK(nv2a_screen_w(1.0f) == 1.0f, "quad w=1");
    CHECK(nv2a_screen_w(2.0f) == 2.0f, "persp w=2");
    CHECK(nv2a_screen_w(4.0f) == 4.0f, "persp w=4");

    /* Surface-space quad: reconstruct host clip coordinates then divide.
     * Both infinity signs are tested; negative w must stay behind the eye. */
    const float xy[4][2] = {{0.5f,0.5f},{640.5f,0.5f},{0.5f,480.5f},{640.5f,480.5f}};
    const float ws[] = {INFINITY, -INFINITY, 1.0f, 2.0f, 4.0f};
    for (unsigned j=0;j<sizeof(ws)/sizeof(ws[0]);j++) {
        float pw=nv2a_screen_w(ws[j]);
        for (unsigned i=0;i<4;i++) {
            float nx=xy[i][0]/320.0f-1.0f, ny=1.0f-xy[i][1]/240.0f;
            float cx=nx*pw, cy=ny*pw;
            CHECK(isfinite(cx) && isfinite(cy) && isfinite(pw), "finite clip quad");
            CHECK(fabsf(cx/pw-nx)<1e-6f && fabsf(cy/pw-ny)<1e-6f, "screen coordinates preserved");
        }
        CHECK((pw<0)==(ws[j]<0), "clip w sign preserved");
    }
    CHECK(nv2a_screen_w(-FLT_MAX)==-FLT_MAX, "negative FLT_MAX preserved");
    CHECK(nv2a_screen_w(-FLT_MIN)==-FLT_MIN, "negative FLT_MIN preserved");
    printf("Tests: %d/%d passed.\n", pass_count, test_count);
    return (pass_count == test_count) ? 0 : 1;
}
