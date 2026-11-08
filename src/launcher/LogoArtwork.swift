import AppKit
import SwiftUI

/// Same logical canvas as the README composition. Keep lettering pixels intact.
struct LogoArtwork: View {
    let logo: NSImage
    let moon: NSImage?

    var body: some View {
        if let moon {
            GeometryReader { bounds in
                let scale = min(bounds.size.width / 1536, bounds.size.height / 1280)
                ZStack(alignment: .topLeading) {
                    Image(nsImage: moon).resizable().interpolation(.high)
                        .frame(width: 1536 * scale, height: 1536 * scale)
                        .position(x: 768 * scale, y: 568 * scale)
                    Image(nsImage: logo).resizable().interpolation(.high).colorInvert()
                        .frame(width: 1536 * scale, height: 1024 * scale)
                        .shadow(color: Color(red: 0.13, green: 0.04, blue: 0.21), radius: 4 * scale)
                        .position(x: 768 * scale, y: 768 * scale)
                }
                .frame(width: 1536 * scale, height: 1280 * scale).clipped()
                .position(x: bounds.size.width / 2, y: bounds.size.height / 2)
            }
        } else {
            Image(nsImage: logo).resizable().interpolation(.high).scaledToFit().colorInvert()
        }
    }
}
