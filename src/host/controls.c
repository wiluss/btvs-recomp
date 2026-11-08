#include "controls.h"
#include "input/keyboard.h"
#include "input/input_names.h"
#include "input/input_map.h"
#include "enhance/mod.h"
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>

/* Numeric protocol v1 follows XBOX_CTL_* explicitly, not INPUT_* order.
 * Host data only: no guest addresses or title hooks. Published before polling. */
_Static_assert(XBOX_CTL_COUNT == 24, "Review the versioned binding protocol after a runtime update");
static const int input_index[24] = {
    INPUT_A,INPUT_B,INPUT_X,INPUT_Y,INPUT_WHITE,INPUT_BLACK,INPUT_LEFT_TRIGGER,INPUT_RIGHT_TRIGGER,
    INPUT_START,INPUT_BACK,INPUT_LEFT_THUMB,INPUT_RIGHT_THUMB,
    INPUT_DPAD_UP,INPUT_DPAD_DOWN,INPUT_DPAD_LEFT,INPUT_DPAD_RIGHT,
    INPUT_LSTICK_UP,INPUT_LSTICK_DOWN,INPUT_LSTICK_LEFT,INPUT_LSTICK_RIGHT,
    INPUT_RSTICK_UP,INPUT_RSTICK_DOWN,INPUT_RSTICK_LEFT,INPUT_RSTICK_RIGHT};
static const WORD bits[8] = {XBOX_GAMEPAD_START,XBOX_GAMEPAD_BACK,XBOX_GAMEPAD_LEFT_THUMB,
    XBOX_GAMEPAD_RIGHT_THUMB,XBOX_GAMEPAD_DPAD_UP,XBOX_GAMEPAD_DPAD_DOWN,XBOX_GAMEPAD_DPAD_LEFT,XBOX_GAMEPAD_DPAD_RIGHT};
static const int analog[8] = {XBOX_BUTTON_A,XBOX_BUTTON_B,XBOX_BUTTON_X,XBOX_BUTTON_Y,
    XBOX_BUTTON_WHITE,XBOX_BUTTON_BLACK,XBOX_BUTTON_LTRIGGER,XBOX_BUTTON_RTRIGGER};
static int pad_sources[16];
static int sticks[2] = {0,1};
static InputBindings key_bindings;

static int key_supported(int n)
{
    return n == 0 || n == 8 || n == 9 || n == 13 || (n >= 16 && n <= 18) || n == 27
        || (n >= 32 && n <= 40) || n == 45 || n == 46 || (n >= 48 && n <= 57)
        || (n >= 65 && n <= 90) || (n >= 96 && n <= 107) || (n >= 109 && n <= 123 && n != 122);
}
static int parse(const char *text, int values[43])
{
    if (!text || strlen(text) > 512) return 0;
    for (int i = 0; i < 43; i++) {
        char *end;
        long n;
        if (!(*text >= '0' && *text <= '9') && *text != '-') return 0;
        errno = 0; n = strtol(text, &end, 10);
        if (end == text || errno || n < -1 || n > 255) return 0;
        if ((i < 42 && *end != ',') || (i == 42 && *end)) return 0;
        values[i] = (int)n; text = end + (i < 42);
    }
    if (values[0] != 1) return 0;
    for (int i = 0; i < 24; i++) {
        if (!key_supported(values[1+i])) return 0;
        for (int j = 0; j < i; j++) if (values[1+i] && values[1+i] == values[1+j]) return 0;
    }
    for (int i = 0; i < 16; i++) {
        if (values[25+i] < -1 || values[25+i] > 15) return 0;
        for (int j = 0; j < i; j++) if (values[25+i] >= 0 && values[25+i] == values[25+j]) return 0;
    }
    for (int i = 41; i < 43; i++) if (values[i] < 0 || values[i] > 2) return 0;
    const int required[] = {0,1,8};
    for (int i = 0; i < 3; i++) if (!values[1+required[i]] && values[25+required[i]] < 0) return 0;
    return 1;
}
int buffy_InputProfileValid(const char *text) { int values[43]; return parse(text, values); }

static BYTE read_button(const XBOX_GAMEPAD *pad, int control)
{
    if (control < 0) return 0;
    if (control < 8) return pad->bAnalogButtons[analog[control]];
    return pad->wButtons & bits[control-8] ? 255 : 0;
}
void buffy_FilterInput(DWORD port, const struct xbox_host_pad *host, XBOX_INPUT_STATE *state)
{
    if (host && host->connected && state) {
        const XBOX_GAMEPAD *raw = &host->pad.Gamepad;
        XBOX_GAMEPAD mapped;
        memset(&mapped, 0, sizeof mapped);
        for (int i = 0; i < 16; i++) {
            BYTE pressure = read_button(raw, pad_sources[i]);
            if (i < 8) mapped.bAnalogButtons[analog[i]] = pressure;
            else if (pressure >= 128) mapped.wButtons |= bits[i-8];
        }
        if (sticks[0] != 2) {
            mapped.sThumbLX = sticks[0] ? raw->sThumbRX : raw->sThumbLX;
            mapped.sThumbLY = sticks[0] ? raw->sThumbRY : raw->sThumbLY;
        }
        if (sticks[1] != 2) {
            mapped.sThumbRX = sticks[1] ? raw->sThumbRX : raw->sThumbLX;
            mapped.sThumbRY = sticks[1] ? raw->sThumbRY : raw->sThumbLY;
        }
        if (port == 0 && xbox_InputKeyboardOn()) {
            uint8_t down[INPUT_KEY_COUNT];
            XBOX_GAMEPAD keyboard;
            for (int k = 0; k < INPUT_KEY_COUNT; k++) down[k] = xbox_FramebufferKeyDown(k) != 0;
            xbox_InputMap_KeysResolve(&key_bindings, down, &keyboard);
            xbox_InputMap_PadMerge(&mapped, &keyboard);
        }
        /* Keep the input core's merged packet number. No second keyboard poll,
         * mouse read, ramp update, trigger threshold or radial deadzone. */
        state->Gamepad = mapped;
    }
    xbox_enhance_pad_filter(port, host, state);
}

void buffy_ConfigureKeyboard(void)
{
    int values[43], have = 0, remap = 0;
    const char *profile = getenv("BUFFY_INPUT_PROFILE");
    xbox_InputBindingsStage();
    const int azerty_ctl[] = {XBOX_CTL_LSTICK_UP,XBOX_CTL_LSTICK_LEFT,XBOX_CTL_A,XBOX_CTL_WHITE};
    const int azerty_key[] = {'Z','Q','W','A'};
    for (int i = 0; i < 4; i++) {
        xbox_InputBindingsClear(azerty_ctl[i]);
        xbox_InputBind(azerty_ctl[i], azerty_key[i], 0);
    }
    xbox_InputBind(XBOX_CTL_LSTICK_UP, XBOX_VK_NUMPAD8, 0);
    xbox_InputBind(XBOX_CTL_LSTICK_LEFT, XBOX_VK_NUMPAD4, 0);
    if (profile) {
        have = parse(profile, values);
        if (!have) fprintf(stderr, "[BUFFY INPUT] invalid profile; using original AZERTY bindings\n");
    }
    if (have) {
        for (int c = 0; c < 24; c++) {
            xbox_InputBindingsClear(c);
            if (values[1+c]) xbox_InputBind(c, values[1+c], 0);
        }
        /* Preserve keypad alternatives unless explicitly assigned elsewhere. */
        const int codes[] = {104,98,100,102};
        for (int c = 16; c < 20; c++) if (values[1+c]) {
            int used = 0;
            for (int j = 0; j < 24; j++) if (values[1+j] == codes[c-16]) used = 1;
            if (!used) xbox_InputBind(c, codes[c-16], 0);
        }
        for (int i = 0; i < 16; i++) { pad_sources[i] = values[25+i]; remap |= pad_sources[i] != i; }
        sticks[0] = values[41]; sticks[1] = values[42];
        remap |= sticks[0] != 0 || sticks[1] != 1;
        fprintf(stderr, "[BUFFY INPUT] custom keyboard profile loaded; pad remap=%d\n", remap != 0);
    }
    memset(&key_bindings, 0, sizeof key_bindings);
    for (int c = 0; c < 24; c++) {
        int codes[4], mouse[4], n = xbox_InputBindingsOf(c, codes, mouse, 4);
        for (int j = 0; j < n && j < 4; j++) if (!mouse[j])
            key_bindings.key[input_index[c]][key_bindings.count[input_index[c]]++] = (uint8_t)codes[j];
    }
    xbox_InputBindingsCommit();
    if (remap) xbox_InputSetPadFilter(buffy_FilterInput);
}
