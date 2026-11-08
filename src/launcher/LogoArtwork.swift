import AppKit
import SwiftUI

/// Same logical canvas as the README composition. Keep lettering pixels intact.
struct LogoArtwork: View {
    let logo: NSImage
    let moon: NSImage?

    var body: some View {
        GeometryReader { bounds in
            let height: CGFloat = moon == nil ? 1024 : 1280
            let scale = min(bounds.size.width / 1536, bounds.size.height / height)
            ZStack(alignment: .topLeading) {
                if let moon {
                    Image(nsImage: moon).resizable().interpolation(.high)
                        .frame(width: 1536 * scale, height: 1536 * scale)
                        .position(x: 768 * scale, y: 568 * scale)
                }
                SilverWordmark(logo: logo, scale: scale)
                    .frame(width: 1536 * scale, height: 1024 * scale)
                    .position(x: 768 * scale, y: (moon == nil ? 512 : 768) * scale)
            }
            .frame(width: 1536 * scale, height: height * scale).clipped()
            .position(x: bounds.size.width / 2, y: bounds.size.height / 2)
        }
    }
}

/// Presentation layers only: the approved lettering mask is never redrawn.
private struct SilverWordmark: View {
    let logo: NSImage
    let scale: CGFloat

    private var lettering: some View {
        Image(nsImage: logo).resizable().interpolation(.high).colorInvert().luminanceToAlpha()
            // luminanceToAlpha replaces alpha; restore the original coverage.
            .mask(Image(nsImage: logo).resizable().interpolation(.high))
    }

    var body: some View {
        ZStack {
            Color(red: 18/255, green: 13/255, blue: 29/255).mask(lettering)
                .offset(x: 7 * scale, y: 9 * scale).blur(radius: 2 * scale)
            Color(red: 243/255, green: 243/255, blue: 245/255).mask(lettering)
                .offset(x: -3 * scale, y: -3 * scale)
            Color(red: 72/255, green: 66/255, blue: 79/255).mask(lettering)
                .offset(x: 3 * scale, y: 3 * scale)
            LinearGradient(stops: [
                .init(color: Color(red: 232/255, green: 233/255, blue: 239/255), location: 0),
                .init(color: Color(red: 185/255, green: 189/255, blue: 200/255), location: 0.30),
                .init(color: Color(red: 247/255, green: 247/255, blue: 250/255), location: 0.48),
                .init(color: Color(red: 196/255, green: 200/255, blue: 211/255), location: 0.63),
                .init(color: Color(red: 162/255, green: 167/255, blue: 180/255), location: 1)
            ], startPoint: .top, endPoint: .bottom).mask(lettering)
        }
    }
}
