import Foundation
import Vision
import CoreImage
import AppKit
// usage: seg framesDir outDir startIdx endIdx (1-based, inclusive). Writes c_NNNNN.png with person alpha.
let a = CommandLine.arguments
let dir = a[1], out = a[2], s = Int(a[3])!, e = Int(a[4])!
try? FileManager.default.createDirectory(atPath: out, withIntermediateDirectories: true)
let ctx = CIContext()
let cs = CGColorSpace(name: CGColorSpace.sRGB)!
for i in s...e {
  let name = String(format: "f_%05d.jpg", i)
  guard let img = CIImage(contentsOf: URL(fileURLWithPath: dir + "/" + name)) else { continue }
  let req = VNGeneratePersonSegmentationRequest()
  req.qualityLevel = .accurate
  req.outputPixelFormat = kCVPixelFormatType_OneComponent8
  let h = VNImageRequestHandler(ciImage: img)
  try h.perform([req])
  guard let m = req.results?.first?.pixelBuffer else { continue }
  var mask = CIImage(cvPixelBuffer: m)
  mask = mask.transformed(by: CGAffineTransform(scaleX: img.extent.width / mask.extent.width, y: img.extent.height / mask.extent.height))
  mask = mask.applyingFilter("CIGaussianBlur", parameters: ["inputRadius": 1.4]).cropped(to: img.extent)
  let res = img.applyingFilter("CIBlendWithMask", parameters: ["inputBackgroundImage": CIImage(color: .clear).cropped(to: img.extent), "inputMaskImage": mask])
  let url = URL(fileURLWithPath: out + "/" + String(format: "c_%05d.png", i))
  try ctx.writePNGRepresentation(of: res, to: url, format: .RGBA8, colorSpace: cs)
}
