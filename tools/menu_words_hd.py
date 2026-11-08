"""Rasterize private, reviewed word outlines in captured texture coordinates."""
import hashlib
from io import BytesIO
import json

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont


def rasterize_word(path, size, scale):
    from font_outline import build_font

    width, height = size
    master = {
        'schema': 1, 'family': 'Menu Word Mask', 'units_per_pixel': 64,
        'em_pixels': 32, 'baseline': 21, 'paths': {'65': path},
    }
    # A synthetic cell for the entire image, with the inclusive UV margin
    # expected by the outline builder. No guest layout or font metrics change.
    layout = {'glyphs': [{
        'code': 65, 'box': [0, 0, width + 1, height + 1],
        'ink': [0, 0, width, height], 'metrics': [0, width, width],
    }]}
    font = ImageFont.truetype(BytesIO(build_font(master, layout)), 32 * scale)
    mask = Image.new('L', (width * scale, height * scale))
    ImageDraw.Draw(mask).text((0, 21 * scale), 'A', font=font, fill=255, anchor='ls')
    if mask.getbbox() is None:
        raise ValueError('Empty word outline')
    return mask


def paint_label(source, coverage, ink_rgb, shadow_rgb):
    # The captured alpha includes the soft outline. Replace its old colored
    # strokes with the new coverage, applying opacity once with source-over.
    background = Image.new('RGBA', coverage.size, (*shadow_rgb, 255))
    background.putalpha(source.getchannel('A').resize(coverage.size, Image.Resampling.LANCZOS))
    foreground = Image.new('RGBA', coverage.size, (*ink_rgb, 255))
    foreground.putalpha(coverage)
    return Image.alpha_composite(background, foreground)


def render_word(source, path, scale, style):
    if source.mode != 'RGBA' or max(source.size) > 256 or type(scale) is not int or scale not in (2, 4, 8):
        raise ValueError('Invalid word image or scale')
    coverage = rasterize_word(path, source.size, scale)
    if style['mode'] == 'gradient':
        # The title has a colored gradient inside its shape. Its decoded
        # transparent texels carry the continuation of that straight RGB field.
        color = source.convert('RGB').resize(coverage.size, Image.Resampling.BICUBIC)
        opacity = source.getchannel('A').filter(ImageFilter.MaxFilter(3))
        opacity = opacity.resize(coverage.size, Image.Resampling.BILINEAR)
        color.putalpha(ImageChops.multiply(coverage, opacity))
        return color
    if style['mode'] == 'ink-and-shadow':
        colors = [style['ink_rgb'], style['shadow_rgb']]
        if any(len(rgb) != 3 or any(type(v) is not int or not 0 <= v <= 255 for v in rgb)
               for rgb in colors):
            raise ValueError('Invalid word palette')
        return paint_label(source, coverage, *colors)
    raise ValueError('Unknown word painting mode')


def prepare_words(root, recipe):
    raw = (root/'private/fonts/menu-words/master.json').read_bytes()
    if hashlib.sha256(raw).hexdigest() != recipe['master_sha256']:
        raise ValueError('Unreviewed word outlines')
    paths = json.loads(raw)
    entries = recipe['entries']
    if not isinstance(paths, dict) or set(paths) != {entry['texture_hash'] for entry in entries}:
        raise ValueError('Word outline coverage differs from recipe')
    result = []
    for entry in entries:
        key = entry['texture_hash']
        if len(key) != 16 or any(c not in '0123456789ABCDEF' for c in key):
            raise ValueError('Invalid word texture identity')
        with Image.open(root/'private/textures/menu-words'/(key+'.png')) as image:
            source = image.convert('RGBA')
        if (source.size != tuple(entry['dimensions'])
            or hashlib.sha256(source.tobytes()).hexdigest() != entry['rgba_sha256']):
            raise ValueError('Unreviewed word source: ' + key)
        result.append((entry, render_word(source, paths[key], recipe['scale'], entry)))
    return result
