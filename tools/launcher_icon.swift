// Original vector icon. All generated PNG/ICNS files stay under build/.
import AppKit
import Foundation

let destination = URL(fileURLWithPath: CommandLine.arguments[1], isDirectory: true)
try FileManager.default.createDirectory(at: destination, withIntermediateDirectories: true)
let image = NSImage(size: NSSize(width: 1024, height: 1024))
image.lockFocus()
// A new hand-drawn monogram, not a tracing of the game's logo or HUD.
let base = NSBezierPath(roundedRect: NSRect(x: 42, y: 42, width: 940, height: 940), xRadius: 211, yRadius: 211)
NSGradient(starting: NSColor(srgbRed: 0.17, green: 0.075, blue: 0.26, alpha: 1),
           ending: NSColor(srgbRed: 0.026, green: 0.015, blue: 0.055, alpha: 1))!.draw(in: base, angle: -65)
NSGraphicsContext.saveGraphicsState()
base.addClip()
let violet = NSColor(srgbRed: 0.62, green: 0.36, blue: 0.88, alpha: 1)
let moon = NSBezierPath(ovalIn: NSRect(x: 280, y: 300, width: 585, height: 585))
let haze = NSShadow(); haze.shadowColor = violet.withAlphaComponent(0.55); haze.shadowBlurRadius = 65; haze.shadowOffset = .zero; haze.set()
NSGradient(starting: NSColor(srgbRed: 0.49, green: 0.40, blue: 0.63, alpha: 1),
           ending: NSColor(srgbRed: 0.13, green: 0.09, blue: 0.23, alpha: 1))!.draw(in: moon, angle: 40)
NSGraphicsContext.restoreGraphicsState()
NSGraphicsContext.saveGraphicsState(); moon.addClip()
for (x,y,w,h) in [(570.0,670.0,145.0,110.0),(697,550,110,145),(455,730,85,61),(480,410,145,108),(728,720,49,44)] {
    NSColor(srgbRed: 0.11, green: 0.075, blue: 0.20, alpha: 0.16).setFill()
    NSBezierPath(ovalIn: NSRect(x:x,y:y,width:w,height:h)).fill()
}
NSGraphicsContext.restoreGraphicsState()
// The stake crosses behind the letter. A restrained red edge echoes the UI.
let stake = NSBezierPath()
stake.move(to: NSPoint(x: 256, y: 172)); stake.line(to: NSPoint(x: 302, y: 150))
stake.line(to: NSPoint(x: 711, y: 731)); stake.line(to: NSPoint(x: 785, y: 891))
stake.line(to: NSPoint(x: 664, y: 771)); stake.close()
NSGradient(starting: NSColor(srgbRed: 0.38, green: 0.045, blue: 0.14, alpha: 1),
           ending: NSColor(srgbRed: 0.82, green: 0.31, blue: 0.35, alpha: 1))!.draw(in: stake, angle: 55)
let grain = NSBezierPath(); grain.move(to: NSPoint(x: 292,y: 193)); grain.line(to: NSPoint(x: 741,y: 829))
NSColor(srgbRed: 1,green: 0.65,blue: 0.59,alpha: 0.48).setStroke(); grain.lineWidth=3; grain.stroke()
// Original asymmetric serif B with open counters and a long lower swash.
let letter = NSBezierPath(); letter.windingRule = .evenOdd
letter.move(to: NSPoint(x: 293,y: 773))
letter.curve(to: NSPoint(x: 551,y: 798),controlPoint1: NSPoint(x: 355,y: 770),controlPoint2: NSPoint(x: 451,y: 811))
letter.curve(to: NSPoint(x: 704,y: 661),controlPoint1: NSPoint(x: 667,y: 790),controlPoint2: NSPoint(x: 714,y: 737))
letter.curve(to: NSPoint(x: 600,y: 544),controlPoint1: NSPoint(x: 704,y: 602),controlPoint2: NSPoint(x: 662,y: 568))
letter.curve(to: NSPoint(x: 724,y: 401),controlPoint1: NSPoint(x: 686,y: 533),controlPoint2: NSPoint(x: 733,y: 484))
letter.curve(to: NSPoint(x: 548,y: 231),controlPoint1: NSPoint(x: 720,y: 281),controlPoint2: NSPoint(x: 638,y: 237))
letter.curve(to: NSPoint(x: 253,y: 228),controlPoint1: NSPoint(x: 436,y: 213),controlPoint2: NSPoint(x: 347,y: 271))
letter.curve(to: NSPoint(x: 326,y: 302),controlPoint1: NSPoint(x: 277,y: 264),controlPoint2: NSPoint(x: 290,y: 296))
letter.line(to: NSPoint(x: 365,y: 314));letter.line(to: NSPoint(x: 365,y: 716));letter.close()
letter.move(to: NSPoint(x: 455,y: 733));letter.line(to: NSPoint(x: 455,y: 571))
letter.curve(to: NSPoint(x: 609,y: 656),controlPoint1: NSPoint(x: 572,y: 558),controlPoint2: NSPoint(x: 612,y: 586))
letter.curve(to: NSPoint(x: 455,y: 733),controlPoint1: NSPoint(x: 612,y: 721),controlPoint2: NSPoint(x: 555,y: 756));letter.close()
letter.move(to: NSPoint(x: 455,y: 509));letter.line(to: NSPoint(x: 455,y: 306))
letter.curve(to: NSPoint(x: 626,y: 407),controlPoint1: NSPoint(x: 562,y: 271),controlPoint2: NSPoint(x: 626,y: 316))
letter.curve(to: NSPoint(x: 455,y: 509),controlPoint1: NSPoint(x: 626,y: 489),controlPoint2: NSPoint(x: 566,y: 516));letter.close()
NSGraphicsContext.saveGraphicsState()
let shadow = NSShadow();shadow.shadowColor = NSColor.black.withAlphaComponent(0.85);shadow.shadowBlurRadius=26;shadow.shadowOffset=NSSize(width: 0,height: -10);shadow.set()
NSGradient(starting: NSColor(srgbRed: 0.74,green: 0.65,blue: 0.85,alpha: 1),
           ending: NSColor(srgbRed: 1,green: 0.97,blue: 0.93,alpha: 1))!.draw(in: letter,angle: 80)
NSGraphicsContext.restoreGraphicsState()
NSColor(srgbRed: 0.92,green: 0.79,blue: 1,alpha: 0.55).setStroke();letter.lineWidth=2;letter.stroke()
NSColor(srgbRed: 0.60,green: 0.39,blue: 0.79,alpha: 0.35).setStroke();base.lineWidth=3;base.stroke()
image.unlockFocus()
for size in [16, 32, 128, 256, 512] {
    for scale in [1, 2] {
        let pixels = size * scale
        let bitmap = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: pixels, pixelsHigh: pixels,
            bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false,
            colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
        NSGraphicsContext.saveGraphicsState()
        NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: bitmap)
        image.draw(in: NSRect(x: 0, y: 0, width: pixels, height: pixels), from: .zero, operation: .copy, fraction: 1)
        NSGraphicsContext.restoreGraphicsState()
        let name = "icon_\(size)x\(size)\(scale == 2 ? "@2x" : "").png"
        try bitmap.representation(using: .png, properties: [:])!.write(to: destination.appendingPathComponent(name))
    }
}
