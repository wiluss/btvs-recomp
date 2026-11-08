#include "nv2a_backend_common.h"
#include "nv2a_vertex_compact.h"
#include <assert.h>
#include <stdio.h>

/* PRIMITIVE_EXPANDER */
static struct nv2a_vertex_map work;
static uint32_t dense[65536], saved[65536];
static unsigned char raw[65536][16];
static float packed_vertices[65536][4];
static unsigned checks;
#define CHECK(x) do { checks++; assert(x); } while (0)

static void check_draws(void)
{
    const uint16_t vertices[] = {100,1500,200,1500,300,65530,100,400};
    const uint32_t types[] = {NV2A_VTX_D3DCOLOR,NV2A_VTX_FLOAT,NV2A_VTX_UBYTE,
                             NV2A_VTX_S1,NV2A_VTX_S32K,NV2A_VTX_CMP};
    for (uint32_t i=0; i<65536; i++)
        for (uint32_t c=0; c<4; c++) {
            uint32_t word=i*UINT32_C(0x9e3779b9)+c*UINT32_C(0x1f123bb5);
            memcpy(raw[i]+4*c,&word,4);
        }
    const uint32_t special[4]={0x80000000u,0x7f800000u,0x7fc01234u,0x7fa01234u};
    memcpy(raw[100],special,16); /* -0, infinity and NaNs keep their bits. */
    for (uint32_t prim=NV_PRIM_POINTS; prim<=NV_PRIM_POLYGON; prim++) {
        enum nv2a_topology topology;
        uint32_t before[24], indices[24], count=0, span=65530-100+1;
        uint32_t n=nv2a_prim_to_list(prim,vertices,8,100,before,&topology);
        CHECK(n>0 && n<=24);
        memcpy(indices,before,n*sizeof *indices);
        CHECK(nv2a_vertex_compact(indices,n,span,&work,&count)==1);
        CHECK(count>0 && count<=8);
        for (uint32_t j=0; j<n; j++) {
            CHECK(indices[j]<count);
            CHECK(work.source[indices[j]]==before[j]); /* order/winding retained */
        }
        for (unsigned t=0; t<sizeof types/sizeof types[0]; t++)
            for (uint32_t size=1; size<=4; size++) {
                for (uint32_t i=0; i<count; i++)
                    CHECK(nv2a_vtx_decode(types[t],size,raw[100+work.source[i]],packed_vertices[i]));
                for (uint32_t j=0; j<n; j++) {
                    float expected[4];
                    CHECK(nv2a_vtx_decode(types[t],size,raw[100+before[j]],expected));
                    CHECK(memcmp(expected,packed_vertices[indices[j]],16)==0);
                }
            }
    }
}

int main(void)
{
    uint32_t n, sparse[]={63,0,63,4095,64,0}, high[]={65535,0,65535};
    uint32_t bad[]={63,0,4096}, empty=77, edge[]={3,1,3,2};
    CHECK(nv2a_vertex_compact(sparse,6,4096,&work,&n)==1 && n==4);
    const uint32_t wanted[]={0,1,0,2,3,1};
    CHECK(memcmp(sparse,wanted,sizeof wanted)==0);
    CHECK(work.source[0]==63 && work.source[1]==0 && work.source[2]==4095 && work.source[3]==64);
    CHECK(nv2a_vertex_compact(high,3,65536,&work,&n)==1 && n==2);
    CHECK(work.source[0]==65535 && high[0]==high[2] && high[0]!=high[1]);
    memcpy(saved,bad,sizeof bad);
    CHECK(nv2a_vertex_compact(bad,3,4096,&work,&n)==0 && n==4096);
    CHECK(memcmp(bad,saved,sizeof bad)==0); /* failure cannot partially rewrite */
    CHECK(nv2a_vertex_compact(NULL,0,100,&work,&n)==0 && n==100);
    CHECK(nv2a_vertex_compact(&empty,1,0,&work,&n)==0 && n==0 && empty==77);
    CHECK(nv2a_vertex_compact(&empty,1,UINT32_MAX,&work,&n)==0 && n==UINT32_MAX && empty==77);
    CHECK(nv2a_vertex_compact(edge,4,4,&work,&n)==1 && n==3); /* exact 3/4 threshold */
    for (uint32_t i=0; i<65536; i++) dense[i]=i;
    memcpy(saved,dense,sizeof dense);
    CHECK(nv2a_vertex_compact(dense,65536,65536,&work,&n)==0 && n==65536);
    CHECK(memcmp(dense,saved,sizeof dense)==0); /* all 65536 unique: no uint16 wrap */
    check_draws();
    printf("vertex compaction: %u checks passed\n",checks);
    return 0;
}
