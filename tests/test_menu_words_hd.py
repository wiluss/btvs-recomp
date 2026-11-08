"""Word image coverage and native XRTP text-kind regressions."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from menu_words_hd import paint_label, render_word
from text_pack import compose
from texture_pilot import write_pack
import test_texture_pilot as texture_tests


class WordImageTests(unittest.TestCase):
    def test_title_mask_keeps_canvas_position_counter_and_straight_color(self):
        source = Image.new('RGBA', (12, 8), (122, 77, 200, 220))
        path = 'M1 1H11V7H1Z M3 2V6H9V2Z'
        word = render_word(source, path, 8, {'mode': 'gradient'})
        self.assertEqual(word.size, (96, 64))
        self.assertEqual(word.getchannel('A').getbbox(), (8, 8, 88, 56))
        self.assertEqual(word.getpixel((16, 24)), (122, 77, 200, 220))
        self.assertEqual(word.getpixel((48, 32)), (122, 77, 200, 0))

    def test_label_composites_coverage_once(self):
        source = Image.new('RGBA', (1, 1), (99, 17, 12, 64))
        coverage = Image.new('L', (1, 1), 128)
        label = paint_label(source, coverage, (255, 0, 0), (0, 0, 255))
        self.assertEqual(label.getpixel((0, 0)), (204, 0, 51, 160))
        self.assertEqual(source.getpixel((0, 0)), (99, 17, 12, 64))

    def test_native_text_toggle_keeps_font_and_art(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            art, label = root/'art.png', root/'word.png'
            Image.new('RGBA', (4, 4), (255, 0, 0, 255)).save(art)
            Image.new('RGBA', (16, 16), (170, 187, 204, 221)).save(label)

            def row(key, kind, image):
                return {'hash':key, 'width':2, 'height':2, 'kind':kind,
                        'image':image, 'mipmaps':False}

            base, text, combined = root/'base.xrtp', root/'text.xrtp', root/'combined.xrtp'
            write_pack([row(1, 'art', art)], base, 2)
            write_pack([row(2, 'font', label), row(3, 'text', label)], text, 8)
            self.assertEqual(compose(base, text, combined), 3)
            source, exe = root/'reader.c', root/'reader'
            source.write_text('''#include "nv2a_tex_pack.h"
#include <assert.h>
int main(int argc, char **argv) {
    char error[256];
    assert(argc == 2 && nv2a_tex_pack_load(argv[1], error, sizeof error) == 3);
    assert(nv2a_tex_pack_scale() == 2 && nv2a_tex_pack_text_scale() == 8);
    struct nv2a_tex_pack_entry *word = nv2a_tex_pack_find(3, 2, 2);
    assert(word && word->width == 16 && word->levels == 1);
    assert(nv2a_tex_pack_texels(word)[0] == 0xDDAABBCCu);
    nv2a_tex_pack_set_kind_enabled(XRTP_KIND_TEXT, 0);
    assert(nv2a_tex_pack_find(1, 2, 2));
    assert(nv2a_tex_pack_find(2, 2, 2));
    assert(!nv2a_tex_pack_find(3, 2, 2));
    nv2a_tex_pack_unload();
    return 0;
}
''')
            texture_tests.TextureTests().compile(exe, [source,
                ROOT/'vendor/xboxrecomp/src/kernel/nv2a_tex_pack.c',
                ROOT/'vendor/xboxrecomp/src/kernel/nv2a_backend_common.c'])
            subprocess.run([str(exe), str(combined)], check=True, capture_output=True)


if __name__ == '__main__':
    unittest.main()
