#include "nv2a_tex_pack.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
int main(int argc,char **argv) {
    assert(argc==5);char error[128];
    assert(nv2a_tex_pack_load(argv[1],error,sizeof error)==2);
    struct nv2a_tex_pack_entry *base=nv2a_tex_pack_find(1,4,4);
    assert(base&&nv2a_tex_pack_texels(base)[0]==0xff0000ff);
    uint32_t gen=nv2a_tex_pack_gen();
    for(int n=0;n<300;n++) {
        assert(nv2a_tex_pack_overlay_load(argv[2],error,sizeof error)==1);
        assert(nv2a_tex_pack_gen()!=gen);gen=nv2a_tex_pack_gen();
        struct nv2a_tex_pack_entry *skin=nv2a_tex_pack_find(1,4,4);
        assert(skin&&nv2a_tex_pack_texels(skin)[0]==0xffff0000);
        struct nv2a_tex_pack_entry *untouched=nv2a_tex_pack_find(2,4,4);
        assert(untouched&&nv2a_tex_pack_texels(untouched)[0]==0xff00ff00);
        assert(nv2a_tex_pack_overlay_load(argv[3],error,sizeof error)<0);
        assert(nv2a_tex_pack_gen()==gen);
        assert(nv2a_tex_pack_texels(nv2a_tex_pack_find(1,4,4))[0]==0xffff0000);
        assert(nv2a_tex_pack_overlay_load(argv[4],error,sizeof error)<0);
        assert(nv2a_tex_pack_gen()==gen);
        nv2a_tex_pack_overlay_clear();assert(nv2a_tex_pack_gen()!=gen);gen=nv2a_tex_pack_gen();
        assert(nv2a_tex_pack_texels(nv2a_tex_pack_find(1,4,4))[0]==0xff0000ff);
    }
    nv2a_tex_pack_set_enabled(0);assert(!nv2a_tex_pack_find(1,4,4));nv2a_tex_pack_set_enabled(1);
    nv2a_tex_pack_unload();assert(nv2a_tex_pack_count()==0);
    assert(nv2a_tex_pack_overlay_load(argv[2],error,sizeof error)==1);
    assert(nv2a_tex_pack_count()==1);
    assert(nv2a_tex_pack_texels(nv2a_tex_pack_find(1,4,4))[0]==0xffff0000);
    nv2a_tex_pack_unload();assert(nv2a_tex_pack_count()==0);
    puts("300 transactional skin/base cycles, failed replacement preservation, lazy source ownership and generation invalidation passed.");
}
