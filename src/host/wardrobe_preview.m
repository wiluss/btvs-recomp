/* Local screenshot thumbnails, decoded once before guest/render threads. */
#include <math.h>
#include <ImageIO/ImageIO.h>
#include <CoreGraphics/CoreGraphics.h>
#include <stdlib.h>
#include <string.h>
unsigned *buffy_WardrobePreview(const char *path)
{
    if (!path || !*path) return NULL;
    CFURLRef url = CFURLCreateFromFileSystemRepresentation(NULL, (const UInt8 *)path, strlen(path), false);
    if (!url) return NULL;
    CGImageSourceRef source = CGImageSourceCreateWithURL(url, NULL); CFRelease(url);
    if (!source) return NULL;
    int cap = 512; CFNumberRef number = CFNumberCreate(NULL, kCFNumberIntType, &cap);
    const void *keys[] = {kCGImageSourceCreateThumbnailFromImageAlways,kCGImageSourceThumbnailMaxPixelSize,kCGImageSourceCreateThumbnailWithTransform};
    const void *values[] = {kCFBooleanTrue,number,kCFBooleanTrue};
    CFDictionaryRef options = CFDictionaryCreate(NULL,keys,values,3,&kCFTypeDictionaryKeyCallBacks,&kCFTypeDictionaryValueCallBacks);
    CGImageRef image = CGImageSourceCreateThumbnailAtIndex(source,0,options);
    CFRelease(options); CFRelease(number); CFRelease(source);
    if (!image) return NULL;
    unsigned *pixels = calloc(512*288,4);
    CGColorSpaceRef colors = CGColorSpaceCreateDeviceRGB();
    CGContextRef ctx = pixels ? CGBitmapContextCreate(pixels,512,288,8,512*4,colors,kCGImageAlphaPremultipliedLast|kCGBitmapByteOrder32Big) : NULL;
    CGColorSpaceRelease(colors);
    if (!ctx) { free(pixels); CGImageRelease(image); return NULL; }
    double w=CGImageGetWidth(image),h=CGImageGetHeight(image),scale=fmin(512/w,288/h);
    CGContextTranslateCTM(ctx,0,288); CGContextScaleCTM(ctx,1,-1);
    CGContextDrawImage(ctx,CGRectMake((512-w*scale)/2,(288-h*scale)/2,w*scale,h*scale),image);
    CGContextRelease(ctx); CGImageRelease(image); return pixels;
}
