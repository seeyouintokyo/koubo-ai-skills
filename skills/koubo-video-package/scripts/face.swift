import Foundation
import Vision
import AppKit
let dir = CommandLine.arguments[1]
let step = Int(CommandLine.arguments[2])!
let files = try FileManager.default.contentsOfDirectory(atPath: dir).filter{$0.hasPrefix("f_")}.sorted()
for (i,f) in files.enumerated() where i % step == 0 {
  guard let img = NSImage(contentsOfFile: dir+"/"+f), let cg = img.cgImage(forProposedRect:nil,context:nil,hints:nil) else {continue}
  let req = VNDetectFaceRectanglesRequest()
  try? VNImageRequestHandler(cgImage: cg).perform([req])
  if let b = (req.results ?? []).max(by:{$0.boundingBox.width<$1.boundingBox.width})?.boundingBox {
    print(String(format:"%d,%.4f,%.4f,%.4f,%.4f", i, b.midX, 1-b.midY, b.width, b.height))
  }
}
