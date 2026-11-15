/* Adversarial native ABI and ownership fixture; no game data. */
static uint32_t bump=0x200000, meta=0x900000, player=0x100000;
static uint32_t manager=0x110000, pausemenu=0x120000, wardrobe=0x130000;
static unsigned allocated_count, released_count, mesh_deletes, gui_deletes, unlocks;
static unsigned locks, snapshots, light_calls, native_pause_loads, current_menu, focus;
static uint32_t expected_render_matrix;
static unsigned physics_reads;
static unsigned cutscene_running, cutscene_queries;
static struct {uint32_t p;int freed;} allocations[512];
static uint32_t mdata(unsigned n){uint32_t p=meta;meta+=(n+15u)&~15u;memset((void*)XBOX_PTR(p),0,n);return p;}
static void finish(unsigned popped,uint32_t result){
 uint32_t next=g_esp+popped;
#define SPOIL(t,n) n=(t)29;
 SCALARS(SPOIL)
#undef SPOIL
 memset(g_fp_stack,0xD2,sizeof g_fp_stack);
#define SPOILV(i) memset(&g_xmm##i,0xAB,sizeof g_xmm##i);memset(&g_mm##i,0xCD,sizeof g_mm##i);
 SPOILV(0) SPOILV(1) SPOILV(2) SPOILV(3) SPOILV(4) SPOILV(5) SPOILV(6) SPOILV(7)
#undef SPOILV
 g_esp=next;g_eax=result;
}
static void release(uint32_t p){
 for(unsigned i=0;i<allocated_count;i++)if(allocations[i].p==p){assert(!allocations[i].freed);allocations[i].freed=1;released_count++;return;}
 assert(!"Released unowned guest object");
}
void sub_002BC1A0(void){uint32_t bytes=MEM32(g_esp+4),p=bump;assert(bytes<0x10000&&allocated_count<512);bump+=(bytes+15)&~15u;memset((void*)XBOX_PTR(p),0,bytes);allocations[allocated_count++].p=p;finish(4,p);}
void sub_002BC1A8(void){release(MEM32(g_esp+4));finish(4,0);}
static void skin(uint32_t p){
 MEM32(p)=0x697DBC;uint32_t pose=mdata(0x28),handle=mdata(16),data=mdata(0x200),impl=mdata(8),instance=mdata(4);
 MEM32(data)=0x61AB0C;MEM32(data+12)=1;MEM32(data+16)=mdata(0x48);
 MEM32(p+0x1AC)=pose;MEM32(pose+8)=2;MEM32(p+0x10)=handle;MEM32(handle+4)=data;
 MEM32(p+4)=impl;MEM32(impl+4)=instance;MEM32(instance)=data;
 MEM32(data+0x1B4)=2;MEM32(data+0x1B8)=mdata(2*0x12C);MEM32(data+0x1D8)=mdata(0x74);
 MEM32(data+0x1BC)=mdata(96);uint32_t parents=mdata(8);MEM32(parents)=0xffffffff;MEM32(parents+4)=0;MEM32(data+0x1C0)=parents;
 uint32_t names=mdata(8);MEM32(handle+12)=names;
 for(unsigned i=0;i<2;i++){uint32_t node=mdata(76);MEM32(names+4*i)=node;strcpy((char*)XBOX_PTR(node+12),i?"spine":"root");}
}
void sub_00285920(void){skin(g_ecx);finish(4,g_ecx);}
void sub_00285D20(void){assert(MEM32(g_esp+8)==0&&MEM32(g_esp+12)==1);finish(16,1);}
void sub_00285C10(void){assert(MEM32(g_esp+4)==1);release(g_ecx);mesh_deletes++;finish(8,0);}
void sub_001273F0(void){MEM32(g_ecx+0x78)=0x1256;finish(4,g_ecx);}
void sub_0012DD20(void){
 uint32_t index=MEM32(g_esp+12),path=MEM32(g_ecx+0x30+16*index);assert(index<5&&MEM32(g_esp+8)==0x61FB98&&MEM32(g_esp+16)==0);
 assert(!strncmp((char*)XBOX_PTR(path),"recomp_live\\",12));finish(20,0);
}
void sub_002ABB50(void){assert(MEM32(g_ecx)==0x1256);MEM32(g_ecx)=0;finish(4,0);}
void sub_0021B650(void){MEM32(g_ecx)=CHARACTER_VTABLE;finish(4,g_ecx);}
void sub_0021B9D0(void){assert(MEM32(g_ecx+0x274)==preview_info&&MEM32(g_ecx+0x30C)<5);finish(4,1);}
void sub_0021B740(void){assert(MEM32(g_ecx)==CHARACTER_VTABLE);assert(MEM32(g_esp+4)==0);gui_deletes++;finish(8,0);}
void sub_002B7160(void){assert(strstr((char*)XBOX_PTR(MEM32(g_esp+4)),".boneanim"));assert(MEM32(g_esp+8)==1);finish(12,0);}
void sub_00043D60(void){assert(MEM32(g_esp+8)==0xA&&MEM32(g_esp+12)==0);locks++;finish(16,0x160000+locks*16);}
void sub_0003BBE0(void){assert(MEM32(g_esp+4)>0x160000);unlocks++;finish(8,1);}
void sub_00093FB0(void){finish(4,player);}
void sub_000943E0(void){cutscene_queries++;finish(4,cutscene_running?0xABCD0001:0xABCD0000);}
static void transformation(void){physics_reads++;finish(4,0x170000);}
void (*recomp_lookup(uint32_t va))(void){assert(va==0x50100);return transformation;}
void sub_0001F7B0(void){memset((void*)XBOX_PTR(MEM32(g_esp+4)),0x37,84);snapshots++;finish(8,0);}
void sub_0001F890(void){assert(MEM8(MEM32(g_esp+4))==0x37);finish(8,0);}
void sub_002859A0(void){assert(MEM32(g_esp+4)==expected_render_matrix&&MEM32(g_esp+8)==0&&MEM32(g_esp+12)==0x3F800000);uint32_t data=MEM32(MEM32(g_ecx+0x10)+4);memcpy((void*)XBOX_PTR(MEM32(data+16)+24),(void*)XBOX_PTR(expected_render_matrix),48);finish(16,0);}
void sub_00286150(void){assert(MEM32(g_esp+8)==2);uint32_t ids=MEM32(g_esp+12);assert(MEM32(ids)==10&&MEM32(ids+4)==20);light_calls++;finish(16,0);}
void sub_00223760(void){assert(!buffy_OutfitsPauseLoad(g_ecx));native_pause_loads++;finish(4,0);}
void sub_001EE130(void){MEM32(g_ecx+0x24)=MEM32(g_esp+4);finish(8,0);}
void sub_001EA460(void){focus=MEM32(g_esp+4);finish(8,0);}
void sub_001EBE00(void){current_menu=MEM32(g_esp+4);if(current_menu==9)assert(buffy_OutfitsPauseLoad(pausemenu));finish(12,0);}
void sub_00218B70(void){finish(4,0);}
void sub_00218C20(void){finish(8,0);}
void sub_00222470(void){assert(MEM32(g_ecx+0x1C)==1);finish(4,0);}
void sub_001ECB90(void){finish(8,0);}
int xbox_GuestCpuRelease(int kind,uint32_t va){(void)kind;(void)va;assert(!"No worker in this fixture");return 0;}
void xbox_GuestCpuAcquire(void){assert(!"No worker in this fixture");}
static void check_cpu(const CpuState *expected){CpuState actual;memset(&actual,0,sizeof actual);save_cpu(&actual);assert(!memcmp(expected,&actual,sizeof actual));}
static void wrong_frame(void){finish(16,0);}
int main(int argc,char **argv){
 g_esp=0x1F0000;g_eflags=0x246;g_df=1;g_fp_stack[3]=-1.25;g_fp_top=7;g_fp_control_word=0x37f;g_fp_cc=0x4100;g_mxcsr=0x1f80;
 memset(&g_xmm6,0xB4,sizeof g_xmm6);memset(&g_mm7,0xC3,sizeof g_mm7);
 CpuState expected;memset(&expected,0,sizeof expected);save_cpu(&expected);
 if(argc>1&&!strcmp(argv[1],"bad")){uint32_t a[4]={1,2,3,4};invoke_args(wrong_frame,0,4,a,0);return 99;}
 MEM32(MANAGER_GLOBAL)=manager;MEM32(manager)=MANAGER_VTABLE;MEM32(0x77BB14)=0x151000;MEM32(0x151008)=0x152000;
 MEM32(pausemenu)=0x68D9F4;MEM32(pausemenu+0x1C)=9;
 uint32_t button=0x140000;MEM32(button+4)=pausemenu;MEM32(button+0x1C)=0x200;MEM32(pausemenu+0x30)=0x141000;MEM32(0x141000)=button;
 assert(buffy_OutfitsPauseLoad(pausemenu));assert(MEM32(button+0x24)==1);check_cpu(&expected);
 for(unsigned cycle=0;cycle<2;cycle++){
  MEM32(player)=0x180000;MEM32(0x1801F8)=0x50100;MEM32(player+0x274)=INFO_SLAYER;MEM8(player+0x384)=1;MEM32(player+0x27C)=3;
  uint32_t original=mdata(0x220),state=mdata(0x198);skin(original);MEM32(player+0x414)=original;MEM32(player+0x4BC)=state;MEM32(state+0x60)=original;
  uint32_t source_data=MEM32(MEM32(original+0x10)+4);
  expected_render_matrix=MEM32(source_data+16)+24;
  MEM32(original+0x148)=2;MEM32(original+0x48)=10;MEM32(original+0x68)=20;
  unsigned char actor_before[0xE80],state_before[0x198];memcpy(actor_before,(void*)XBOX_PTR(player),sizeof actor_before);memcpy(state_before,(void*)XBOX_PTR(state),sizeof state_before);
  if(!cycle){owner=manager;unsigned before=allocated_count;buffy_OutfitsResourcesReady();assert(allocated_count==before&&!body_actor);owner=0;check_cpu(&expected);}
  buffy_OutfitsResourcesReady();check_cpu(&expected);assert(ready()&&gameplay_previews&&body_actor==player&&MEM32(models[0]+0x30C)==3);
  unsigned count=allocated_count;buffy_OutfitsResourcesReady();assert(allocated_count==count);check_cpu(&expected);
  assert(buffy_OutfitsPauseMessage(pausemenu,button,5));assert(current_menu==16);check_cpu(&expected);
  assert(!buffy_OutfitsPauseMessage(pausemenu,button,6));assert(!buffy_OutfitsPauseMessage(pausemenu,button+4,5));
  MEM32(wardrobe)=MENU_VTABLE;MEM32(wardrobe+0x1C)=16;
  for(unsigned i=0;i<6;i++){uint32_t node=0x142000+16*i,control=0x143000+128*i;MEM32(node)=control;MEM32(node+4)=i==5?0:node+16;MEM32(control+4)=wardrobe;MEM32(control+0x1C)=ids[i];}
  MEM32(wardrobe+0x30)=0x142000;
  assert(buffy_OutfitsLoad(wardrobe));check_cpu(&expected);
  assert(buffy_OutfitsMessage(wardrobe,0x143000+2*128,5));assert(choice==2&&current_menu==9&&focus==85);check_cpu(&expected);
  cutscene_running=1;unsigned before_pose=snapshots,before_lights=light_calls;
  assert(buffy_OutfitsRender(original)==original);check_cpu(&expected);
  assert(choice==2&&snapshots==before_pose&&light_calls==before_lights);
  cutscene_running=0;
  uint32_t cosmetic=body_models[1];assert(buffy_OutfitsRender(original)==cosmetic);check_cpu(&expected);assert(snapshots==cycle*4+1&&light_calls==cycle*4+1);
  for(unsigned frame=0;frame<3;frame++){
   /* A second cutscene between gameplay draws must not discard the choice. */
   cutscene_running=1;assert(buffy_OutfitsRender(original)==original);check_cpu(&expected);assert(choice==2);
   cutscene_running=0;
   MEM32(expected_render_matrix+36)=0x3F800000+(frame<<23);
   assert(buffy_OutfitsRender(original)==cosmetic);check_cpu(&expected);
   uint32_t part=MEM32(MEM32(MEM32(cosmetic+0x10)+4)+16);
   assert(!memcmp((void*)XBOX_PTR(part+24),(void*)XBOX_PTR(expected_render_matrix),48));
  }
  MEM32(source_data)=0;assert(buffy_OutfitsRender(original)==original);MEM32(source_data)=0x61AB0C;
  MEM32(source_data+12)=0;assert(buffy_OutfitsRender(original)==original);MEM32(source_data+12)=1;
  uint32_t saved_part=MEM32(source_data+16);MEM32(source_data+16)=0x03FFFFF0;assert(buffy_OutfitsRender(original)==original);MEM32(source_data+16)=saved_part;
  check_cpu(&expected);
  assert(!memcmp(actor_before,(void*)XBOX_PTR(player),sizeof actor_before));assert(!memcmp(state_before,(void*)XBOX_PTR(state),sizeof state_before));
  uint32_t data=MEM32(MEM32(cosmetic+0x10)+4),parents=MEM32(data+0x1C0);MEM32(parents+4)=1;assert(buffy_OutfitsRender(original)==original);MEM32(parents+4)=0;
  uint32_t impl=MEM32(cosmetic+4),instance=MEM32(impl+4),owner_data=MEM32(instance);MEM32(owner_data+0x1B4)=513;assert(buffy_OutfitsRender(original)==original);MEM32(owner_data+0x1B4)=2;
  uint32_t names=MEM32(MEM32(cosmetic+0x10)+12),name=MEM32(names)+12;MEM8(name)='X';assert(buffy_OutfitsRender(original)==original);MEM8(name)='r';check_cpu(&expected);
  MEM32(wardrobe+0x3C)=0x142000+5*16;buffy_OutfitsUpdate(wardrobe);assert(MEM32(manager+0x74)==models[5]);
  assert(buffy_OutfitsCommand(wardrobe,0x29));assert(choice==2&&current_menu==9&&focus==85&&MEM32(manager+0x74)==models[2]);check_cpu(&expected);
  assert(buffy_OutfitsKeepImage(9)&&buffy_OutfitsKeepImage(16)&&!buffy_OutfitsKeepImage(8)&&!buffy_OutfitsKeepImage(17));
  buffy_OutfitsActorDestroy(player+4);assert(body_actor==player);buffy_OutfitsActorDestroy(player);check_cpu(&expected);
  assert(!body_actor&&!owner&&!MEM32(manager+0x74)&&allocated_count==released_count);
  unsigned freed=released_count;buffy_OutfitsActorDestroy(player);assert(freed==released_count);
  player+=0x2000;
 }
 assert(cutscene_queries&&physics_reads==0&&snapshots==8&&light_calls==8);
 assert(mesh_deletes==10&&gui_deletes==12&&locks==8&&unlocks==8);
 return 0;
}
