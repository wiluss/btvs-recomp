/* Diagnostic decoder using the pinned generic XboxRecomp implementation.
 * No game decoder or asset data is incorporated in this source. */
#include "nv2a_backend_common.h"
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#include <stdint.h>

static unsigned number(const char *s)
{
    char *end;
    unsigned long n;
    errno = 0;
    n = strtoul(s, &end, 10);
    if (!*s || *end || errno || n > 2048) exit(2);
    return (unsigned)n;
}

int main(int argc, char **argv)
{
    unsigned fmt, w, h, pitch, levels, bytes;
    size_t count;
    FILE *input, *output;
    uint8_t *raw;
    uint32_t *pixels;
    if (argc != 8) return 2;
    fmt=number(argv[1]); w=number(argv[2]); h=number(argv[3]);
    pitch=number(argv[4]); levels=number(argv[5]);
    if ((fmt!=12 && fmt!=14 && fmt!=15) || !w || !h || pitch || !levels
        || levels>12 || (w&(w-1)) || (h&(h-1))) return 2;
    { unsigned dim=w>h?w:h, max_levels=1; while (dim>1) {dim>>=1;max_levels++;}
      if (levels>max_levels) return 2; }
    bytes=nv2a_tex_extent(fmt,w,h,pitch,levels);
    count=nv2a_tex_texels(w,h,levels);
    raw=malloc(bytes); pixels=malloc(count*4);
    if (!raw || !pixels) return 3;
    input=fopen(argv[6],"rb");
    if (!input || fread(raw,1,bytes,input)!=bytes || fgetc(input)!=EOF) return 4;
    fclose(input);
    nv2a_tex_decode(raw,fmt,w,h,pitch,levels,NULL,0,pixels);
    output=fopen(argv[7],"wb");
    if (!output || fwrite(pixels,4,(size_t)w*h,output)!=(size_t)w*h || fclose(output)) return 5;
    printf("%016llX\n",(unsigned long long)nv2a_tex_hash(raw,bytes,NV2A_TEX_HASH_SEED));
    free(raw);free(pixels);return 0;
}
