#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <sys/mman.h>
#define XBOX_CONTIG_SIZE (64u << 20)
#define XBOX_HEAP_BASE 0x01000000u
#define XBOX_HEAP_TOP XBOX_CONTIG_SIZE
#define CONTIG_PAGE 4096
#define CONTIG_PAGES (XBOX_CONTIG_SIZE / CONTIG_PAGE)
static volatile uint8_t g_phys_image_named[CONTIG_PAGES];
static volatile uint8_t g_phys_ram_named[CONTIG_PAGES];
static uint8_t contig[CONTIG_PAGES];
static uint32_t g_xbox_image_lo = 0x00200000, g_xbox_image_hi = 0x00400000;
static size_t g_xbox_total_ram = 128u << 20, g_xbox_map_size;
static uint8_t *g_apu_ram_ptr;
static const uint8_t *xbox_ContiguousPageMap(void) { return contig; }
static uint32_t xbox_ContiguousAllocatedBytes(void) { return 0x03000000; }
/* PRODUCTION_FUNCTIONS */
#define CHECK(x) do { if (!(x)) { fprintf(stderr, "line %d: %s\n", __LINE__, #x); return 1; } } while (0)
int main(void)
{
    const uint32_t image = 0x00202040, heap = 0x01234040;
    const size_t mapped = (size_t)0x88000000u;
    g_apu_ram_ptr = mmap(NULL, mapped, PROT_READ | PROT_WRITE,
                        MAP_PRIVATE | MAP_ANON, -1, 0);
    CHECK(g_apu_ram_ptr != MAP_FAILED);
    contig[image >> 12] = contig[(image >> 12) + 1] = contig[heap >> 12] = 1;
    g_apu_ram_ptr[image] = 0;
    g_apu_ram_ptr[0x80000000u + image] = 0xA5;
    CHECK(*mcpx_apu_sample_phys(image) == 0xA5); /* unnamed stays window */
    xbox_PhysNoteRamName(image & ~4095u);
    CHECK(*mcpx_apu_sample_phys(image) == 0);
    CHECK(*mcpx_apu_phys(image) == 0xA5); /* SGE/voice table/notifier unchanged */
    CHECK(mcpx_apu_sample_phys(image + 4096) == g_apu_ram_ptr + 0x80000000u + image + 4096);
    CHECK(!strcmp(mcpx_apu_sample_phys_class(image), "image-named"));
    CHECK(!strcmp(mcpx_apu_phys_class(image), "win"));
    CHECK(!g_phys_ram_named[image >> 12]);
    CHECK(mcpx_apu_sample_phys(0x80000000u + image) == g_apu_ram_ptr + image);
    /* Heap ownership still wins over the window for BOTH kinds of reads. */
    xbox_PhysNoteRamName(heap);
    CHECK(mcpx_apu_sample_phys(heap) == g_apu_ram_ptr + heap);
    CHECK(mcpx_apu_phys(heap) == g_apu_ram_ptr + heap);
    g_phys_ram_named[heap >> 12] = 0;
    CHECK(mcpx_apu_sample_phys(heap) == g_apu_ram_ptr + 0x80000000u + heap);
    /* Guard before indexing: high RAM, wrap, and the last low-memory page. */
    xbox_PhysNoteRamName(0x04000000u);
    xbox_PhysNoteRamName(UINT32_MAX);
    CHECK(mcpx_apu_sample_phys(0x05000000u) == g_apu_ram_ptr + 0x05000000u);
    CHECK(mcpx_apu_sample_phys(0x09000000u) == g_apu_ram_ptr + 0x01000000u);
    CHECK(mcpx_apu_sample_phys(0x03FFFFFFu) == mcpx_apu_phys(0x03FFFFFFu));
    CHECK(munmap(g_apu_ram_ptr, mapped) == 0);
    puts("APU image DMA: assertions passed");
    return 0;
}
