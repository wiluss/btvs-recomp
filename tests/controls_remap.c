#include "controls.h"
#include "input/keyboard.h"
#include "input/input_map.h"
#include "input/input_names.h"
#include "platform/recomp_env.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static xbox_input_pad_filter_fn installed;
void xbox_InputSetPadFilter(xbox_input_pad_filter_fn fn) { installed = fn; }
void xbox_enhance_pad_filter(DWORD port, const struct xbox_host_pad *host, XBOX_INPUT_STATE *state)
{ (void)port; (void)host; (void)state; }
const char *recomp_env_value_[RENV_COUNT];
volatile int recomp_env_ready_ = 1;
void recomp_env_init(void) {}
int xbox_InputMouseHeld(int code) { (void)code; assert(0 && "unexpected mouse read"); return 0; }
void xbox_InputMouseTick(uint64_t now, int clock) { (void)now; (void)clock; assert(0 && "unexpected mouse tick"); }
int xbox_InputMouseLook(int *x, int *y) { (void)x; (void)y; assert(0 && "unexpected mouse motion read"); return 0; }

static const int base[24] = {87,88,67,86,65,69,49,51,13,8,16,17,38,40,37,39,90,83,81,68,73,75,74,76};
static int override_a;
static void profile(int target, int source, int left, int right)
{
    char text[512]; size_t n = (size_t)snprintf(text,sizeof text,"1");
    for (int i=0;i<24;i++) n += (size_t)snprintf(text+n,sizeof text-n,",%d",i==0 && override_a?override_a:base[i]);
    for (int i=0;i<16;i++) n += (size_t)snprintf(text+n,sizeof text-n,",%d",i==target?source:i==source?target:i);
    snprintf(text+n,sizeof text-n,",%d,%d",left,right);
    assert(buffy_InputProfileValid(text));
    setenv("BUFFY_INPUT_PROFILE",text,1);buffy_ConfigureKeyboard();
}
static void button(XBOX_GAMEPAD *pad,int index,int pressure)
{
    static const int analog[] = {0,1,2,3,5,4,6,7};
    static const int bits[] = {0x10,0x20,0x40,0x80,1,2,4,8};
    if(index<8)pad->bAnalogButtons[analog[index]]=(BYTE)pressure;
    else if(pressure)pad->wButtons |= (WORD)bits[index-8];
}
static int button_value(const XBOX_GAMEPAD *pad,int index)
{
    static const int analog[] = {0,1,2,3,5,4,6,7};
    static const int bits[] = {0x10,0x20,0x40,0x80,1,2,4,8};
    return index<8?pad->bAnalogButtons[analog[index]]:(pad->wButtons & bits[index-8]?255:0);
}
int main(int argc,char **argv)
{
    if(argc>1){char line[2048];while(fgets(line,sizeof line,stdin)){line[strcspn(line,"\r\n")]=0;printf("%d\n",buffy_InputProfileValid(line));}return 0;}
    (void)argv;
    unsetenv("BUFFY_INPUT_PROFILE");buffy_ConfigureKeyboard();assert(installed==NULL);
    int codes[4],mouse[4];assert(xbox_InputBindingsOf(XBOX_CTL_LSTICK_UP,codes,mouse,4)==2 && codes[0]=='Z' && codes[1]==104);
    assert(xbox_InputBindingsOf(XBOX_CTL_A,codes,mouse,4)==1 && codes[0]=='W');
    xbox_InputKeyboardEnable(0);
    for(int target=0;target<16;target++)for(int source=0;source<16;source++) {
        profile(target,source,0,1);
        for(int input=0;input<16;input++) {
            struct xbox_host_pad host;XBOX_INPUT_STATE st;
            memset(&host,0,sizeof host);host.connected=1;button(&host.pad.Gamepad,input,255);
            host.pad.Gamepad.sThumbLX=-32768;host.pad.Gamepad.sThumbLY=32767;
            host.pad.Gamepad.sThumbRX=1234;host.pad.Gamepad.sThumbRY=-5678;
            st=host.pad;st.dwPacketNumber=123; buffy_FilterInput(1,&host,&st);
            for(int out=0;out<16;out++) {
                int from=out==target?source:out==source?target:out;
                assert(button_value(&st.Gamepad,out)==(from==input?255:0));
            }
            assert(st.dwPacketNumber==123 && st.Gamepad.sThumbLX==-32768 && st.Gamepad.sThumbRY==-5678);
        }
    }
    profile(8,6,1,0);
    for(int pressure=0;pressure<=255;pressure++) {
        struct xbox_host_pad host;XBOX_INPUT_STATE st;
        memset(&host,0,sizeof host);host.connected=1;button(&host.pad.Gamepad,6,pressure);
        host.pad.Gamepad.sThumbLX=-32768;host.pad.Gamepad.sThumbRY=32767;st=host.pad;
        buffy_FilterInput(3,&host,&st);
        assert(button_value(&st.Gamepad,8)==(pressure>=128?255:0));
        assert(st.Gamepad.sThumbLY==32767 && st.Gamepad.sThumbRX==-32768);
    }
    profile(0,1,0,1);xbox_InputKeyboardEnable(1);xbox_InputKeysClear();xbox_InputKeySet('W',1);xbox_InputKeySet('Z',1);
    struct xbox_host_pad host;XBOX_INPUT_STATE st,kb,after;
    memset(&host,0,sizeof host);host.connected=1;host.pad.Gamepad.bAnalogButtons[0]=219;
    st=host.pad;xbox_InputKbmState(&kb,1,0);xbox_InputMap_PadMerge(&st.Gamepad,&kb.Gamepad);st.dwPacketNumber=987;
    buffy_FilterInput(0,&host,&st);xbox_InputKbmState(&after,1,0);
    assert(st.Gamepad.bAnalogButtons[0]==255 && st.Gamepad.bAnalogButtons[1]==219 && st.Gamepad.sThumbLY==32767);
    assert(st.dwPacketNumber==987 && after.dwPacketNumber==kb.dwPacketNumber+1);
    host.connected=0;XBOX_INPUT_STATE before=st;buffy_FilterInput(0,&host,&st);assert(memcmp(&before,&st,sizeof st)==0);
    memset(&host,0,sizeof host);host.connected=1;
    for(int key=0;key<28;key++) {
        static const int keypad[] = {104,98,100,102};
        xbox_InputKeysClear();xbox_InputKeySet(key<24?base[key]:keypad[key-24],1);
        xbox_InputKbmState(&kb,1,0);memset(&st,0,sizeof st);st.dwPacketNumber=77;
        buffy_FilterInput(0,&host,&st);
        assert(memcmp(&st.Gamepad,&kb.Gamepad,sizeof st.Gamepad)==0 && st.dwPacketNumber==77);
    }
    override_a=104;profile(0,1,0,1);
    assert(xbox_InputBindingsOf(XBOX_CTL_LSTICK_UP,codes,mouse,4)==1 && codes[0]=='Z');
    xbox_InputKeysClear();xbox_InputKeySet(104,1);memset(&st,0,sizeof st);
    buffy_FilterInput(0,&host,&st);assert(st.Gamepad.bAnalogButtons[0]==255 && st.Gamepad.sThumbLY==0);
    override_a=0;profile(3,-1,2,2);memset(&host,0,sizeof host);host.connected=1;
    host.pad.Gamepad.sThumbLX=-32768;host.pad.Gamepad.sThumbRY=32767;button(&host.pad.Gamepad,3,255);
    st=host.pad;buffy_FilterInput(1,&host,&st);
    assert(st.Gamepad.sThumbLX==0 && st.Gamepad.sThumbRY==0 && button_value(&st.Gamepad,3)==0);
    xbox_InputKeysClear();
    puts("4096 source/destination cases, analog threshold, stick swap, disconnected host, independent keyboard and packet preservation passed.");
    return 0;
}
