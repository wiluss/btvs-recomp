/* Native stock wardrobe. Enabled only with a locally compiled resource pack.
 * Addresses are bound by tools/native_outfits_fix.py to the supported XBE.
 * All callbacks run on the guest thread; no renderer-thread guest calls. */
#define RECOMP_GENERATED_CODE
#include "recomp_funcs.h"
#include "kernel/kernel.h"
#include <stdio.h>
#include <execinfo.h>
#include <spawn.h>
#include <sys/wait.h>
#include <errno.h>
extern char **environ;
#include <stdlib.h>
#include <string.h>

#define COUNT 6
#define MANAGER_GLOBAL 0x007E6BD0u
#define INFO_SLAYER 0x00765D40u
#define MENU_VTABLE 0x0068D534u
#define CHARACTER_VTABLE 0x0068C724u
#define MANAGER_VTABLE 0x0068C5C4u
const char *buffy_OutfitsBindingProtocol;
static uint32_t owner, models[COUNT], preview_info;
#define INFO_BYTES (0x2Cu + 6u*16u)
#define INFO_ALLOCATION (INFO_BYTES + 5u*64u)
static unsigned choice;
static int configured, enabled;
static int gameplay_previews, pause_return;
static unsigned return_menu=1;
static uint32_t body_actor, body_original, body_models[5], pose_scratch, idle_locks[4];
static int loading;
static void forget_body(void);
static const uint32_t ids[COUNT] = {1,2,3,0x83,0x200,0x201};

#define SCALARS(X) \
 X(uint32_t,g_eax) X(uint32_t,g_ecx) X(uint32_t,g_edx) X(uint32_t,g_esp) \
 X(uint32_t,g_ebx) X(uint32_t,g_esi) X(uint32_t,g_edi) X(uint32_t,g_ebp) \
 X(uint32_t,g_seh_ebp) X(uint32_t,g_fs_base) X(uint32_t,g_eflags) X(int,g_df) \
 X(int,g_fp_top) X(uint16_t,g_fp_control_word) X(int,g_fp_cmp) X(uint16_t,g_fp_cc) \
 X(uint32_t,g_mxcsr)
#define MEMBER(t,n) t saved_##n;
typedef struct CpuState { SCALARS(MEMBER) double fp[8]; RecompXmm xv[8]; RecompMmx mv[8]; } CpuState;
#undef MEMBER
static void save_cpu(CpuState *s)
{
#define SAVE(t,n) s->saved_##n = n;
    SCALARS(SAVE)
#undef SAVE
    memcpy(s->fp,g_fp_stack,sizeof s->fp);
#define SAVEV(i) s->xv[i]=g_xmm##i; s->mv[i]=g_mm##i;
    SAVEV(0) SAVEV(1) SAVEV(2) SAVEV(3) SAVEV(4) SAVEV(5) SAVEV(6) SAVEV(7)
#undef SAVEV
}
static void restore_cpu(const CpuState *s)
{
#define RESTORE(t,n) n=s->saved_##n;
    SCALARS(RESTORE)
#undef RESTORE
    memcpy(g_fp_stack,s->fp,sizeof s->fp);
#define RESTOREV(i) g_xmm##i=s->xv[i]; g_mm##i=s->mv[i];
    RESTOREV(0) RESTOREV(1) RESTOREV(2) RESTOREV(3) RESTOREV(4) RESTOREV(5) RESTOREV(6) RESTOREV(7)
#undef RESTOREV
}
static void fail(const char *message)
{
    fprintf(stderr,"[OUTFITS] %s\n",message);
    exit(3);
}
static int valid(uint32_t p, uint32_t bytes)
{
    return p>=0x10000u && bytes<=0x04000000u && p<=0x04000000u-bytes;
}
/* Pinned thiscall/stdcall routines pop arguments; the two allocation routines
 * are cdecl. Restore every TLS register, FP/SIMD and flag after each call.
 * The original stack frame remains owned by the injected call site. */
static uint32_t invoke_args(void (*fn)(void), uint32_t self, unsigned argc,
                            const uint32_t *args, int caller_cleanup)
{
    CpuState s; uint32_t result, before=g_esp;
    if (!fn || argc>4 || !valid(before-64,64)) fail("Invalid guest-call frame");
    save_cpu(&s);
    for (unsigned i=argc;i;i--) PUSH32(g_esp,args[i-1]);
    PUSH32(g_esp,0x002183C1u); /* reviewed constructor continuation */
    g_ecx=self;
    fn();
    if (caller_cleanup) g_esp+=argc*4;
    if (g_esp!=before) fail("Guest-call stack contract differs");
    result=g_eax;
    restore_cpu(&s);
    return result;
}
static uint32_t invoke(void (*fn)(void), uint32_t self, unsigned argc,
                       uint32_t a0, uint32_t a1, int caller_cleanup)
{
    uint32_t args[2]={a0,a1};
    if (argc>2) fail("Invalid guest-call frame");
    return invoke_args(fn,self,argc,args,caller_cleanup);
}
static int active(void)
{
    if (!configured) {
        const char *v=getenv("BUFFY_NATIVE_OUTFITS");
        enabled=v && !strcmp(v,"1"); configured=1;
        const char *initial=getenv("BUFFY_NATIVE_OUTFIT_CHOICE");
        if (enabled && initial) {
            char *end;errno=0;long parsed=strtol(initial,&end,10);
            if (errno || !*initial || *end || parsed<0 || parsed>=COUNT)
                fail("Invalid initial stock outfit choice");
            choice=(unsigned)parsed;
        }
    }
    return enabled;
}
static int ready(void)
{
    return active() && valid(owner,0x78) && owner==MEM32(MANAGER_GLOBAL)
        && MEM32(owner)==MANAGER_VTABLE && models[0] && models[5];
}
static int pause_enabled(void)
{
    const char *value=getenv("BUFFY_NATIVE_OUTFITS_PAUSE");
    return active() && value && !strcmp(value,"1");
}
static int is_menu(uint32_t menu)
{
    return valid(menu,0x60) && MEM32(menu)==MENU_VTABLE;
}
static uint32_t find_control(uint32_t menu, uint32_t id)
{
    uint32_t node=MEM32(menu+0x30);
    for (unsigned n=0;node && n<64;n++) {
        if (!valid(node,8)) return 0;
        uint32_t item=MEM32(node);
        if (!valid(item,0x28) || MEM32(item+4)!=menu) return 0;
        if (MEM32(item+0x1C)==id) return item;
        node=MEM32(node+4);
    }
    return 0;
}
static void prepare_choice(unsigned selected)
{
    const char *preview=getenv("BUFFY_NATIVE_OUTFITS_PREVIEW_ONLY");
    if (preview && !strcmp(preview,"1")) return;
    const char *python=getenv("BUFFY_OUTFIT_PYTHON"), *script=getenv("BUFFY_OUTFIT_PREPARER");
    const char *source=getenv("BUFFY_OUTFIT_SOURCE"), *title=getenv("BUFFY_OUTFIT_TITLE");
    const char *cache=getenv("BUFFY_OUTFIT_CACHE");
    if (!python || !script || !source || !title || !cache)
        fail("Stock outfit preparation environment is missing");
    char number[12];snprintf(number,sizeof number,"%u",selected);
    char *args[]={(char*)python,(char*)script,"--source",(char*)source,
        "--title",(char*)title,"--cache",(char*)cache,"--choice",number,"--select-only",
        pause_enabled()?"--pause":NULL,NULL};
    pid_t child;int status;
    fprintf(stderr,"[OUTFITS] saving stock choice %u\n",selected);
    int error=posix_spawn(&child,python,NULL,NULL,args,environ);
    if (error) fail("Cannot start stock outfit preparation");
    /* No guest calls while blocked: let audio/streaming workers run. */
    int released=xbox_GuestCpuRelease(XBOX_GUEST_CPU_HOST,0x002226B0u);
    pid_t waited;
    do { waited=waitpid(child,&status,0); } while (waited<0 && errno==EINTR);
    if (released) xbox_GuestCpuAcquire();
    if (waited<0) fail("Cannot supervise outfit preparation");
    if (!WIFEXITED(status) || WEXITSTATUS(status)!=0)
        fail("Outfit selection could not be saved; restart before selecting again");
}

static void set_menu(unsigned id)
{
    invoke(sub_001EBE00,owner,2,id,1,0);
}
void buffy_OutfitsConstruct(uint32_t manager)
{
    if (!active()) return;
    if (!valid(manager,0x78) || MEM32(manager)!=MANAGER_VTABLE)
        fail("Unexpected native menu manager");
    uint32_t original=MEM32(manager+0x74);
    if (!original) return; /* gameplay HUD manager has no menu character */
    if (owner) fail("Duplicate native preview manager");
    if (!valid(original,0x324) || MEM32(original)!=CHARACTER_VTABLE)
        fail("Unexpected original preview character");
    fprintf(stderr,"[OUTFITS] protocol=%s\n",buffy_OutfitsBindingProtocol?buffy_OutfitsBindingProtocol:"unbound");
    owner=manager;models[0]=original;
    static const char *const preview_names[5] = {
        "buffybronze", "buffyworkout", "buffycheer", "buffyslayer", "darkslayer"
    };
    preview_info=invoke(sub_002BC1A0,0,1,INFO_ALLOCATION,0,1);
    if (!valid(preview_info,INFO_ALLOCATION)) fail("Cannot allocate preview metadata");
    memset((void*)XBOX_PTR(preview_info),0,INFO_ALLOCATION);
    memcpy((void*)XBOX_PTR(preview_info),(const void*)XBOX_PTR(INFO_SLAYER),INFO_BYTES-16u);
    for (unsigned i=0;i<5;i++) {
        uint32_t path=preview_info+INFO_BYTES+i*64u;
        snprintf((char*)XBOX_PTR(path),64,"%s\\%s",
                 gameplay_previews?"recomp_live":"recomp_outfits",preview_names[i]);
        MEM32(preview_info+0x30+i*16)=path;
        MEM32(preview_info+0x34+i*16)=0; /* menu never requests low-resolution models */
    }
    for (unsigned i=1;i<COUNT;i++) {
        uint32_t object=invoke(sub_002BC1A0,0,1,0x324,0,1);
        if (!valid(object,0x324)) fail("Cannot allocate outfit preview");
        invoke(sub_0021B650,object,0,0,0,0);
        if (MEM32(object)!=CHARACTER_VTABLE) fail("Preview constructor differs");
        MEM32(object+0x274)=preview_info;
        MEM32(object+0x30C)=i-1;
        if (!(invoke(sub_0021B9D0,object,0,0,0,0)&255u))
            fail("Original outfit preview failed to load");
        models[i]=object;
        fprintf(stderr,"[OUTFITS] loaded preview %u object=%08X\n",i,object);
    }
    MEM32(manager+0x74)=models[choice];
}
void buffy_OutfitsDestroy(uint32_t manager)
{
    if (!active() || manager!=owner) return;
    MEM32(manager+0x74)=gameplay_previews?0:models[0];
    for (unsigned i=gameplay_previews?0:1;i<COUNT;i++) if (models[i]) {
        /* Scalar deleting destructor: explicit flags=0 retains the allocation. */
        invoke(sub_0021B740,models[i],1,0,0,0);
        invoke(sub_002BC1A8,0,1,models[i],0,1);
    }
    if (preview_info) invoke(sub_002BC1A8,0,1,preview_info,0,1);
    preview_info=0;memset(models,0,sizeof models);owner=0;
    gameplay_previews=0;pause_return=0;return_menu=1;
}
int buffy_OutfitsLoad(uint32_t menu)
{
    if (!ready() || !is_menu(menu) || MEM32(menu+0x1C)!=16) return 0;
    /* Reuse the verified native main-menu initialization role. Restore the
     * distinct menu identity before accepting commands or drawing a frame. */
    MEM32(menu+0x1C)=1;
    invoke(sub_00222470,menu,0,0,0,0);
    MEM32(menu+0x1C)=16;
    invoke(sub_00218B70,menu,0,0,0,0); /* publish the actual menu role */
    for (unsigned i=0;i<COUNT;i++) {
        uint32_t control=find_control(menu,ids[i]);
        if (!control) fail("Wardrobe control missing");
        invoke(sub_001EE130,control,1,0,0,0); /* all stock choices available */
    }
    invoke(sub_001EA460,menu,1,ids[choice],0,0);
    fprintf(stderr,"[OUTFITS] opened native wardrobe\n");
    return 1;
}
int buffy_OutfitsCommand(uint32_t menu, uint32_t command)
{
    if (!ready() || !is_menu(menu) || MEM32(menu+0x1C)!=16) return 0;
    invoke(sub_00218C20,menu,1,command,0,0);
    if (command==0x29) { MEM32(owner+0x74)=models[choice];pause_return=return_menu==9;set_menu(return_menu); }
    else invoke(sub_001ECB90,menu,1,command,0,0);
    return 1;
}
int buffy_OutfitsMessage(uint32_t menu, uint32_t sender, uint32_t message)
{
    if (active() && getenv("BUFFY_NATIVE_OUTFITS_TRACE") && valid(menu,0x28) && message==5)
        fprintf(stderr,"[OUTFITS] event menu=%08X vt=%08X mid=%u sender=%08X parent=%08X id=%u ready=%d\n",menu,MEM32(menu),MEM32(menu+0x1C),sender,valid(sender,0x28)?MEM32(sender+4):0,valid(sender,0x28)?MEM32(sender+0x1C):0,ready());
    if (!ready() || !is_menu(menu) || message!=5 || !valid(sender,0x28)
        || MEM32(sender+4)!=menu) return 0;
    uint32_t id=MEM32(sender+0x1C), mid=MEM32(menu+0x1C);
    if (mid==1 && id==0x200) {return_menu=1;set_menu(16);return 1;}
    if (mid!=16) return 0;
    for (unsigned i=0;i<COUNT;i++) if (id==ids[i]) {
        if (choice!=i) prepare_choice(i);
        choice=i;MEM32(owner+0x74)=models[i];
        fprintf(stderr,"[OUTFITS] selected stock choice %u\n",i);
        pause_return=return_menu==9;set_menu(return_menu);return 1;
    }
    if (id==0x202) {MEM32(owner+0x74)=models[choice];pause_return=return_menu==9;set_menu(return_menu);return 1;}
    return 0;
}
void buffy_OutfitsUpdate(uint32_t menu)
{
    if (!ready() || !is_menu(menu)) return;
    unsigned shown=choice;
    if (MEM32(menu+0x1C)==16) {
        uint32_t node=MEM32(menu+0x3C);
        if (valid(node,8)) {
            uint32_t control=MEM32(node);
            if (valid(control,0x28) && MEM32(control+4)==menu)
                for (unsigned i=0;i<COUNT;i++) if (MEM32(control+0x1C)==ids[i]) shown=i;
        }
    } else if (MEM32(menu+0x1C)!=1) return;
    if (getenv("BUFFY_NATIVE_OUTFITS_TRACE")) {
        static uint32_t last_menu;static unsigned last_shown=99;
        if (last_menu!=menu || last_shown!=shown) {
            fprintf(stderr,"[OUTFITS] preview menu=%u index=%u object=%08X\n",MEM32(menu+0x1C),shown,models[shown]);
            last_menu=menu;last_shown=shown;
        }
    }
    MEM32(owner+0x74)=models[shown];
}

void buffy_OutfitsDiagnosticAbort(uint32_t message)
{
    if (active() && getenv("BUFFY_NATIVE_OUTFITS_TRACE") && valid(message,512)) {
        fprintf(stderr,"[OUTFITS] native abort: %.511s\n",(const char*)XBOX_PTR(message));
        void *frames[32];int count=backtrace(frames,32);backtrace_symbols_fd(frames,count,2);
        exit(3);
    }
}

/* Cosmetic meshes never replace the actor's gameplay mesh or animation state. */
static uint32_t resource_manager(void)
{
    uint32_t root=MEM32(0x0077BB14u);
    return valid(root,12)?MEM32(root+8):0;
}
static uint32_t allocate_guest(uint32_t bytes)
{
    uint32_t p=invoke(sub_002BC1A0,0,1,bytes,0,1);
    if (!valid(p,bytes)) fail("Cannot allocate native wardrobe data");
    return p;
}
static void release_guest(uint32_t p)
{
    if (p) invoke(sub_002BC1A8,0,1,p,0,1);
}
static int same_skeleton(uint32_t a, uint32_t b)
{
    if (!valid(a,0x220)||!valid(b,0x220)||MEM32(a)!=0x697DBCu||MEM32(b)!=0x697DBCu) return 0;
    uint32_t ap=MEM32(a+0x1AC),bp=MEM32(b+0x1AC);
    if (!valid(ap,0x28)||!valid(bp,0x28)) return 0;
    uint32_t n=MEM32(ap+8),m=MEM32(bp+8),am=MEM32(a+0x10),bm=MEM32(b+0x10);
    if (!n||n>512||n!=m||!valid(am,16)||!valid(bm,16)) return 0;
    uint32_t aa=MEM32(am+4),bb=MEM32(bm+4),an=MEM32(am+12),bn=MEM32(bm+12);
    if (!valid(aa,0x1C4)||!valid(bb,0x1C4)||!valid(an,n*4)||!valid(bn,n*4)) return 0;
    uint32_t pa=MEM32(aa+0x1C0),pb=MEM32(bb+0x1C0);
    if (!valid(pa,n*4)||!valid(pb,n*4)||memcmp((void*)XBOX_PTR(pa),(void*)XBOX_PTR(pb),n*4)) return 0;
    for (unsigned i=0;i<n;i++) {
        uint32_t na=MEM32(an+i*4),nb=MEM32(bn+i*4);
        if (!valid(na,76)||!valid(nb,76)) return 0;
        const char *sa=(const char*)XBOX_PTR(na+12),*sb=(const char*)XBOX_PTR(nb+12);
        if (!memchr(sa,0,64)||!memchr(sb,0,64)||strcmp(sa,sb)) return 0;
    }
    return 1;
}
static int snapshot_owner(uint32_t mesh, uint32_t n)
{
    uint32_t impl=MEM32(mesh+4);
    if (!valid(impl,8)) return 0;
    uint32_t instance=MEM32(impl+4);
    if (!valid(instance,4)) return 0;
    uint32_t data=MEM32(instance);
    return valid(data,0x1DC) && MEM32(data+0x1B4)==n
        && valid(MEM32(data+0x1B8),n*0x12C)
        && valid(MEM32(data+0x1D8),0x74);
}
uint32_t buffy_OutfitsRender(uint32_t self)
{
    if (!pause_enabled()||!choice||self!=body_original||!valid(body_actor,0xE80)
        ||MEM32(body_actor+0x414)!=self) return self;
    /* TGO::Cine_IsCutsceneRunning is the retail cdecl/no-argument query.
     * Bone snapshots do not include facial mesh/phoneme channels. Keep the
     * original mesh's complete Render_Base path during a cutscene; the saved
     * choice stays intact and resumes at the next gameplay draw. */
    if (invoke(sub_000943E0,0,0,0,0,1)&255u) return self;
    uint32_t target=body_models[choice-1];
    if (!same_skeleton(self,target)) return self;
    uint32_t n=MEM32(MEM32(self+0x1AC)+8);
    if (!snapshot_owner(self,n)||!snapshot_owner(target,n)||!valid(pose_scratch,0x4000)) return self;
    uint32_t aa=MEM32(MEM32(self+0x10)+4),bb=MEM32(MEM32(target+0x10)+4);
    uint32_t src=MEM32(aa+0x1BC),dst=MEM32(bb+0x1BC),lights=MEM32(self+0x148);
    if (!valid(src,n*48)||!valid(dst,n*48)||lights>8) return self;
    /* UpdateMesh stores the render-interpolated world matrix at part+0x18.
     * The actor's physics transform advances at tick cadence and must not replace
     * it during drawing. Source: supported TMeshModelInstance::UpdateMesh. */
    if (MEM32(aa)!=0x0061AB0Cu || !MEM32(aa+0xC) || MEM32(aa+0xC)>64) return self;
    uint32_t part=MEM32(aa+0x10);
    if (!valid(part,0x48)) return self;
    uint32_t matrix=part+0x18;
    invoke(sub_0001F7B0,MEM32(self+4),1,pose_scratch,0,0);
    invoke(sub_0001F890,MEM32(target+4),1,pose_scratch,0,0);
    uint32_t update[3]={matrix,0,0x3F800000u};
    invoke_args(sub_002859A0,target,3,update,0);
    memcpy((void*)XBOX_PTR(dst),(const void*)XBOX_PTR(src),n*48);
    uint32_t ids=pose_scratch+0x3F00;
    for (unsigned i=0;i<lights;i++) MEM32(ids+i*4)=MEM32(self+0x48+i*0x20);
    uint32_t lighting[3]={MEM8(self+0x14),lights,ids};
    invoke_args(sub_00286150,target,3,lighting,0);
    return target;
}
static void forget_body(void)
{
    uint32_t previous=body_actor;
    if (gameplay_previews && owner) buffy_OutfitsDestroy(owner);
    for (unsigned i=0;i<5;i++) if (body_models[i]) {
        invoke(sub_00285C10,body_models[i],1,1,0,0);body_models[i]=0;
    }
    uint32_t rm=resource_manager();
    for (unsigned i=0;i<4;i++) if (idle_locks[i]) {
        if (!valid(rm,4)) fail("Wardrobe resource manager ended before its owners");
        invoke(sub_0003BBE0,rm,1,idle_locks[i],0,0);idle_locks[i]=0;
    }
    release_guest(pose_scratch);pose_scratch=0;body_actor=0;body_original=0;
    if (previous) fprintf(stderr,"[OUTFITS] released native Pause wardrobe actor=%08X\n",previous);
}
void buffy_OutfitsActorDestroy(uint32_t actor)
{
    if (body_actor && actor==body_actor) forget_body();
}
static void load_pause_previews(uint32_t actor)
{
    static const char *const idle_names[4]={
        "buffy_idle_standing_menu", "buffy_idle_standingll", "buffy_idle_standinglr", "buffy_idle_standing_brushoff"
    };
    uint32_t manager=MEM32(MANAGER_GLOBAL),rm=resource_manager();
    if (!valid(manager,0x78)||MEM32(manager)!=MANAGER_VTABLE||MEM32(manager+0x74)||owner||!valid(rm,4))
        fail("Unexpected native Pause preview manager");
    for (unsigned i=0;i<4;i++) {
        uint32_t file=allocate_guest(0x180);
        snprintf((char*)XBOX_PTR(file+0x84),0xFC,"animation\\buffyfinal_move\\%s.boneanim",idle_names[i]);
        invoke(sub_002B7160,file,2,file+0x84,1,0);
        uint32_t lock[3]={file,0xA,0};idle_locks[i]=invoke_args(sub_00043D60,rm,3,lock,0);
        release_guest(file);
        if (!idle_locks[i]) fail("Native wardrobe idle animation is unavailable");
    }
    uint32_t object=allocate_guest(0x324);
    invoke(sub_0021B650,object,0,0,0,0);
    MEM32(manager+0x74)=object;gameplay_previews=1;
    buffy_OutfitsConstruct(manager);
    MEM32(object+0x274)=preview_info;
    uint32_t index=MEM32(actor+0x27C);
    MEM32(object+0x30C)=index<5?index:0;
    if (!(invoke(sub_0021B9D0,object,0,0,0,0)&255u)) fail("Level outfit preview failed to load");
}
void buffy_OutfitsResourcesReady(void)
{
    if (!pause_enabled()||loading||(owner&&!gameplay_previews)) return;
    uint32_t actor=invoke(sub_00093FB0,0,0,0,0,1);
    if (!valid(actor,0xE80)||MEM32(actor+0x274)!=INFO_SLAYER||!MEM8(actor+0x384)) return;
    uint32_t original=MEM32(actor+0x414),state=MEM32(actor+0x4BC);
    if (!valid(original,0x220)||MEM32(original)!=0x697DBCu||!valid(state,0x198)||MEM32(state+0x60)!=original) return;
    if (body_actor==actor && body_original==original) return;
    loading=1;
    if (body_actor) forget_body();
    body_actor=actor;body_original=original;
    uint32_t info=allocate_guest(INFO_ALLOCATION);
    memset((void*)XBOX_PTR(info),0,INFO_ALLOCATION);
    memcpy((void*)XBOX_PTR(info),(const void*)XBOX_PTR(INFO_SLAYER),INFO_BYTES-16u);
    static const char *const names[5]={"buffybronze","buffyworkout","buffycheer","buffyslayer","darkslayer"};
    for (unsigned i=0;i<5;i++) {
        uint32_t path=info+INFO_BYTES+i*64u;
        snprintf((char*)XBOX_PTR(path),64,"recomp_live\\%s",names[i]);
        MEM32(info+0x30+i*16)=path;MEM32(info+0x34+i*16)=0;
    }
    for (unsigned i=0;i<5;i++) {
        uint32_t spec=allocate_guest(0x84),mesh=allocate_guest(0x220);
        invoke(sub_001273F0,spec,0,0,0,0);
        uint32_t create[4]={spec,0x61FB98u,i,0};invoke_args(sub_0012DD20,info,4,create,0);
        invoke(sub_00285920,mesh,0,0,0,0);
        if (MEM32(mesh)!=0x697DBCu) fail("Cosmetic mesh constructor differs");
        MEM8(mesh+0x39)=MEM8(original+0x39);MEM8(mesh+0x41)=MEM8(original+0x41);
        MEM32(mesh+0x18)=MEM32(original+0x18);
        uint32_t load[3]={spec,0,1};
        if (!(invoke_args(sub_00285D20,mesh,3,load,0)&255u)) fail("Cosmetic outfit failed to load");
        invoke(sub_002ABB50,spec+0x78,0,0,0,0);release_guest(spec);
        body_models[i]=mesh;
        if (!same_skeleton(original,mesh)) fail("Cosmetic outfit skeleton differs from Buffy");
    }
    release_guest(info);pose_scratch=allocate_guest(0x4000);
    load_pause_previews(actor);loading=0;
    fprintf(stderr,"[OUTFITS] native Pause wardrobe ready actor=%08X\n",actor);
}
int buffy_OutfitsPauseMessage(uint32_t menu,uint32_t sender,uint32_t message)
{
    if (!pause_enabled()||!ready()||!gameplay_previews||!valid(menu,0x60)
        ||MEM32(menu)!=0x68D9F4u||MEM32(menu+0x1C)!=9||message!=5
        ||!valid(sender,0x28)||MEM32(sender+4)!=menu||MEM32(sender+0x1C)!=0x200) return 0;
    return_menu=9;set_menu(16);return 1;
}
int buffy_OutfitsPauseLoad(uint32_t menu)
{
    static int entering;
    if (entering||!pause_enabled()||!valid(menu,0x60)||MEM32(menu)!=0x68D9F4u) return 0;
    entering=1;
    invoke(sub_00223760,menu,0,0,0,0);
    entering=0;
    uint32_t control=find_control(menu,0x200);
    if (control) invoke(sub_001EE130,control,1,!(ready()&&gameplay_previews),0,0);
    if (pause_return && ready()) {invoke(sub_001EA460,menu,1,85,0,0);pause_return=0;}
    return 1;
}
int buffy_OutfitsKeepImage(uint32_t id)
{
    return pause_enabled() && id>=9 && id<=16;
}
