"""Export the existing logo with native macOS icon padding; keep branding unchanged."""
import sys
from pathlib import Path
from AppKit import (NSBitmapImageRep, NSGraphicsContext, NSImage, NSDeviceRGBColorSpace,
                    NSBitmapImageFileTypePNG, NSCompositingOperationSourceOver, NSZeroRect, NSBezierPath, NSColor, NSRectFillUsingOperation, NSCompositingOperationCopy)

source = NSImage.alloc().initWithContentsOfFile_(sys.argv[1])
if source is None:
    raise RuntimeError('The source icon could not be loaded.')
bitmap = NSBitmapImageRep.alloc().initWithBitmapDataPlanes_pixelsWide_pixelsHigh_bitsPerSample_samplesPerPixel_hasAlpha_isPlanar_colorSpaceName_bytesPerRow_bitsPerPixel_(None, 1024, 1024, 8, 4, True, False, NSDeviceRGBColorSpace, 0, 0)
context = NSGraphicsContext.graphicsContextWithBitmapImageRep_(bitmap)
NSGraphicsContext.saveGraphicsState()
NSGraphicsContext.setCurrentContext_(context)
NSColor.clearColor().set(); NSRectFillUsingOperation(((0, 0), (1024, 1024)), NSCompositingOperationCopy)
NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(((62, 62), (900, 900)), 198, 198).addClip()
source.drawInRect_fromRect_operation_fraction_(((62, 62), (900, 900)), NSZeroRect, NSCompositingOperationSourceOver, 1)
context.flushGraphics()
NSGraphicsContext.restoreGraphicsState()
data = bitmap.representationUsingType_properties_(NSBitmapImageFileTypePNG, {})
Path(sys.argv[2]).write_bytes(bytes(data))
