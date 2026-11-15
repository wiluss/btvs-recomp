/* Host-only wardrobe, no guest addresses. Tick runs on the walker after
 * backend on_flip: uploads have ended, and GPU commands own GPU copies. */
#include "wardrobe.h"
#include "controls.h"
#include "kernel/nv2a_backend_common.h"
#include "kernel/nv2a_tex_pack.h"
#include "kernel/nv2a_overlay_int.h"
#include "input/keyboard.h"
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <math.h>
#define LIMIT 32
struct outfit { char name[513],path[4097],preview[4097],id[65]; unsigned *pixels; };
static struct outfit items[LIMIT+1];
static unsigned count,choice,active,previous_keys;
static int enabled,s_open,shield,dirty=1;
static char message[160];
static atomic_uint pad_keys,toggle;
static nv2a_flip_hook_fn previous_hook;
static const char *prefs;
enum { LEFT=1,RIGHT=2,CONFIRM=4,CLOSE=8,TOGGLE=16 };
static unsigned read32(FILE *f,int *ok) {
    unsigned char b[4]; if(fread(b,1,4,f)!=4){*ok=0;return 0;}
    return (unsigned)b[0]|(unsigned)b[1]<<8|(unsigned)b[2]<<16|(unsigned)b[3]<<24;
}
static int text(FILE *f,char *dst,size_t cap) {
    int ok=1; unsigned n=read32(f,&ok);
    if(!ok||n>=cap||fread(dst,1,n,f)!=n||memchr(dst,0,n))return 0;
    dst[n]=0;return 1;
}
static int persist(void) {
    if(!prefs||strlen(prefs)>4000)return 0;
    char temp[4096],data[128];snprintf(temp,sizeof temp,"%s.wardrobe-%ld",prefs,(long)getpid());
    int fd=open(temp,O_WRONLY|O_CREAT|O_EXCL,0600);if(fd<0)return 0;
    int n=active?snprintf(data,sizeof data,"{\"version\":1,\"active\":\"%s\"}\n",items[active].id):snprintf(data,sizeof data,"{\"version\":1,\"active\":null}\n");
    int ok=write(fd,data,(size_t)n)==n&&fsync(fd)==0;close(fd);
    if(ok)ok=rename(temp,prefs)==0;
    if(!ok)unlink(temp);return ok;
}
static unsigned keys(void) {
    unsigned k=atomic_load_explicit(&pad_keys,memory_order_relaxed);
    if(xbox_FramebufferKeyDown(37))k|=LEFT;
    if(xbox_FramebufferKeyDown(39))k|=RIGHT;
    if(xbox_FramebufferKeyDown(13))k|=CONFIRM;
    if(xbox_FramebufferKeyDown(27))k|=CLOSE;
    if(xbox_FramebufferKeyDown(119))k|=TOGGLE;
    if(atomic_exchange_explicit(&toggle,0,memory_order_relaxed))k|=TOGGLE;
    return k;
}
void buffy_WardrobeInput(DWORD port,const struct xbox_host_pad *host,XBOX_INPUT_STATE *state) {
    if(!enabled||port!=0||!state)return;
    unsigned k=0;
    static int chord;
    if(host&&host->connected) {
        const XBOX_GAMEPAD *p=&host->pad.Gamepad;
        if(p->wButtons&XBOX_GAMEPAD_DPAD_LEFT)k|=LEFT;
        if(p->wButtons&XBOX_GAMEPAD_DPAD_RIGHT)k|=RIGHT;
        if(p->bAnalogButtons[XBOX_BUTTON_A]>=128)k|=CONFIRM;
        if(p->bAnalogButtons[XBOX_BUTTON_B]>=128)k|=CLOSE;
        int held=(host->extra&XBOX_HOST_GUIDE)&&p->bAnalogButtons[XBOX_BUTTON_Y]>=128;
        if(held&&!chord)atomic_store(&toggle,1);chord=held;
    } else chord=0;
    atomic_store_explicit(&pad_keys,k,memory_order_relaxed);
    if(__atomic_load_n(&s_open,__ATOMIC_ACQUIRE)||__atomic_load_n(&shield,__ATOMIC_ACQUIRE)||xbox_FramebufferKeyDown(119)||chord)
        memset(&state->Gamepad,0,sizeof state->Gamepad);
}
static void draw(void) {
    int x,y,w,h;nv2a_overlay_placement(&x,&y,&w,&h);(void)x;(void)y;
    if(w<=0||h<=0)return;
    mu_Context *ctx=nv2a_overlay_ui_begin(NV2A_OVL_MENU);if(!ctx)return;
    float scale=fminf(w/1000.f,h/700.f);if(scale<0.5f)scale=0.5f;
    int pw=(int)(780*scale),ph=(int)(600*scale),px=(w-pw)/2,py=(h-ph)/2;
    mu_Color white=mu_color(239,226,255,255),muted=mu_color(182,162,205,255);
    nv2a_ovl_ui_rrect(ctx,mu_rect(px,py,pw,ph),12,1,mu_color(18,7,32,245));
    mu_Font title=OVL_FONT(OVL_FONT_TITLE,(int)(32*scale),0),body=OVL_FONT(OVL_FONT_BODY,(int)(22*scale),0);
    mu_draw_text(ctx,title,"BUFFY - WARDROBE",-1,mu_vec2(px+30*scale,py+20*scale),mu_color(185,117,255,255));
    if(items[choice].pixels)nv2a_ovl_ui_image(ctx,mu_rect(px+134*scale,py+85*scale,512*scale,288*scale),1,mu_color(255,255,255,255));
    else mu_draw_text(ctx,body,"No outfit screenshot",-1,mu_vec2(px+230*scale,py+200*scale),muted);
    char label[600];snprintf(label,sizeof label,"%u / %u  %s%s",choice+1,count,items[choice].name,choice==active?"  [ON]":"");
    mu_draw_text(ctx,body,label,-1,mu_vec2(px+30*scale,py+390*scale),white);
    mu_draw_text(ctx,body,"Left/Right or D-pad: browse   Enter/A: wear",-1,mu_vec2(px+30*scale,py+440*scale),muted);
    mu_draw_text(ctx,body,"F8 / Esc / B: close. Pause the game before browsing.",-1,mu_vec2(px+30*scale,py+480*scale),muted);
    mu_draw_text(ctx,body,message,-1,mu_vec2(px+30*scale,py+530*scale),white);
    nv2a_overlay_ui_publish(NV2A_OVL_MENU);
}
static void tick(void) {
    if(previous_hook)previous_hook();
    unsigned k=keys(),pressed=k&~previous_keys;previous_keys=k;
    if((pressed&TOGGLE)||(s_open&&(pressed&CLOSE))) {
        __atomic_store_n(&s_open,!s_open,__ATOMIC_RELEASE);__atomic_store_n(&shield,1,__ATOMIC_RELEASE);dirty=1;
        if(!s_open)nv2a_overlay_hide(NV2A_OVL_MENU);
    }
    if(!s_open){if(!k)__atomic_store_n(&shield,0,__ATOMIC_RELEASE);return;}
    if(pressed&LEFT){choice=(choice+count-1)%count;dirty=1;}
    if(pressed&RIGHT){choice=(choice+1)%count;dirty=1;}
    if((pressed&CONFIRM)&&choice!=active) {
        char error[128];int ok=1;
        if(choice)ok=nv2a_tex_pack_overlay_load(items[choice].path,error,sizeof error)>=0;
        else nv2a_tex_pack_overlay_clear();
        if(ok){active=choice;snprintf(message,sizeof message,persist()?"Outfit applied and saved.":"Outfit applied for this session (preferences not saved).");}
        else snprintf(message,sizeof message,"Skin refused: %.120s",error);
        fprintf(stderr,"[WARDROBE] selection=%u applied=%d\n",choice,ok);dirty=1;
    }
    /* One fixed-size image slot: re-publish only on selection/s_open changes. */
    if(dirty&&items[choice].pixels)nv2a_overlay_image_set(1,items[choice].pixels,512,288);
    static int last_w,last_h;
    int px,py,w,h;nv2a_overlay_placement(&px,&py,&w,&h);
    if(dirty||w!=last_w||h!=last_h){draw();dirty=0;last_w=w;last_h=h;}
}
int buffy_WardrobeEnabled(void){return enabled;}
void buffy_ConfigureWardrobe(void) {
    const char *path=getenv("BUFFY_WARDROBE");if(!path||!*path)return;
    FILE *f=fopen(path,"rb");if(!f){fprintf(stderr,"[WARDROBE] session catalog missing\n");exit(2);}
    char magic[4];int ok=fread(magic,1,4,f)==4&&!memcmp(magic,"BWS1",4);
    unsigned n=read32(f,&ok),selected=read32(f,&ok);
    if(!ok||n>LIMIT||selected>n){fclose(f);fprintf(stderr,"[WARDROBE] invalid catalog header\n");exit(2);}
    strcpy(items[0].name,"Original level outfit");count=n+1;
    for(unsigned i=1;i<count&&ok;i++) {
        ok=text(f,items[i].name,sizeof items[i].name)&&text(f,items[i].path,sizeof items[i].path)&&text(f,items[i].preview,sizeof items[i].preview)&&text(f,items[i].id,sizeof items[i].id);
        if(strlen(items[i].id)!=64||strspn(items[i].id,"0123456789abcdef")!=64)ok=0;
    }
    if(fgetc(f)!=EOF)ok=0;fclose(f);if(!ok){fprintf(stderr,"[WARDROBE] invalid catalog records\n");exit(2);}
    if(nv2a_overlay_arm((1u<<NV2A_OVL_MENU),1080)<0){fprintf(stderr,"[WARDROBE] overlay initialization failed\n");exit(2);}
    for(unsigned i=1;i<count;i++)items[i].pixels=buffy_WardrobePreview(items[i].preview);
    if(selected){char error[128];if(nv2a_tex_pack_overlay_load(items[selected].path,error,sizeof error)<0){fprintf(stderr,"[WARDROBE] initial skin refused: %s\n",error);exit(2);}}
    active=choice=selected;prefs=getenv("BUFFY_WARDROBE_PREFS");
    previous_hook=__atomic_load_n(&nv2a_flip_hook_installed,__ATOMIC_ACQUIRE);
    enabled=1;buffy_InputSetOverlay(buffy_WardrobeInput);nv2a_flip_hook_set(tick);
    fprintf(stderr,"[WARDROBE] ready: %u skins, F8 or Guide+Y; pause before browsing\n",n);
}
