import Foundation
import Vision
import AppKit
// usage: ocr dir → for each frame_*.jpg print  index \t text(y-center)
let dir = CommandLine.arguments[1]
let files = try FileManager.default.contentsOfDirectory(atPath: dir).filter{$0.hasPrefix("f_")}.sorted()
for f in files {
  guard let img = NSImage(contentsOfFile: dir+"/"+f), let cg = img.cgImage(forProposedRect:nil,context:nil,hints:nil) else {continue}
  let req = VNRecognizeTextRequest()
  req.recognitionLanguages = ["zh-Hans","en-US"]
  req.recognitionLevel = .accurate
  try? VNImageRequestHandler(cgImage: cg).perform([req])
  var parts:[String] = []
  for o in req.results ?? [] {
    guard let t = o.topCandidates(1).first else {continue}
    let b = o.boundingBox
    parts.append(String(format:"%@|y=%.2f|h=%.3f|x=%.2f|w=%.2f", t.string, 1-b.midY, b.height, b.midX, b.width))
  }
  print(f + "\t" + parts.joined(separator:" ;; "))
}
