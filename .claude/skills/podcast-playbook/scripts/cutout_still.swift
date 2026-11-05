// Cut the main object out of a still with Apple Vision. Free and local.
//   swiftc -O scripts/cutout_still.swift -o <bin> && <bin> in.png out.png
import Vision
import CoreImage
import Foundation
let a = CommandLine.arguments
let ci = CIImage(contentsOf: URL(fileURLWithPath: a[1]))!
let handler = VNImageRequestHandler(ciImage: ci)
let req = VNGenerateForegroundInstanceMaskRequest()
try handler.perform([req])
guard let r = req.results?.first else { print("no foreground found"); exit(1) }
let buf = try r.generateMaskedImage(ofInstances: r.allInstances, from: handler, croppedToInstancesExtent: true)
let out = CIImage(cvPixelBuffer: buf)
try CIContext().writePNGRepresentation(of: out, to: URL(fileURLWithPath: a[2]), format: .RGBA8, colorSpace: CGColorSpace(name: CGColorSpace.sRGB)!)
print("ok", Int(out.extent.width), Int(out.extent.height))
