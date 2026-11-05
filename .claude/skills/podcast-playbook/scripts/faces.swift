// Face positions and mouth openness over a whole recording, with Apple Vision. Free, local.
//
//   swiftc -O scripts/faces.swift -o /tmp/hf_faces && /tmp/hf_faces IN.mp4 OUT.jsonl [--every 5]
//
// Each line: {"t": seconds, "f": [[cx, cy, w, h, mouth], …]} in source pixels (1920×1080, y down), mouth = inner-lip height / face height.
// Used to frame every shot (the camera was re-framed during the shoot) and to tell who is talking on a single mixed mono track.
import AVFoundation
import Foundation
import Vision

let args = CommandLine.arguments
guard args.count >= 3 else { print("usage: faces IN OUT [--every N]"); exit(2) }
let every = args.firstIndex(of: "--every").flatMap { Int(args[$0 + 1]) } ?? 5
let asset = AVURLAsset(url: URL(fileURLWithPath: args[1]))
let semaphore = DispatchSemaphore(value: 0)
var videoTrack: AVAssetTrack?
Task { videoTrack = try? await asset.loadTracks(withMediaType: .video).first; semaphore.signal() }
semaphore.wait()
guard let track = videoTrack, let reader = try? AVAssetReader(asset: asset) else { print("FAIL: cannot read"); exit(1) }
let W = 960.0, H = 540.0, scale = 2.0
let output = AVAssetReaderTrackOutput(track: track, outputSettings: [
    kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA, kCVPixelBufferWidthKey as String: Int(W), kCVPixelBufferHeightKey as String: Int(H)])
output.alwaysCopiesSampleData = false
reader.add(output)
reader.startReading()
FileManager.default.createFile(atPath: args[2], contents: nil)
guard let out = FileHandle(forWritingAtPath: args[2]) else { print("FAIL: cannot write"); exit(1) }
var n = 0, kept = 0
let started = Date()
while let sample = output.copyNextSampleBuffer() {
    defer { n += 1 }
    if n % every != 0 { continue }
    guard let px = CMSampleBufferGetImageBuffer(sample) else { continue }
    let t = CMSampleBufferGetPresentationTimeStamp(sample).seconds
    let req = VNDetectFaceLandmarksRequest()
    try? VNImageRequestHandler(cvPixelBuffer: px, options: [:]).perform([req])
    var faces: [String] = []
    for o in req.results ?? [] {
        let b = o.boundingBox
        let cx = (b.midX * W) * scale, cy = ((1 - b.midY) * H) * scale, w = (b.width * W) * scale, h = (b.height * H) * scale
        var mouth = -1.0
        if let lips = o.landmarks?.innerLips?.normalizedPoints, lips.count > 2 {
            let ys = lips.map { Double($0.y) }
            mouth = (ys.max()! - ys.min()!)
        }
        faces.append(String(format: "[%.0f,%.0f,%.0f,%.0f,%.3f]", cx, cy, w, h, mouth))
    }
    out.write("{\"t\":\(String(format: "%.2f", t)),\"f\":[\(faces.joined(separator: ","))]}\n".data(using: .utf8)!)
    kept += 1
    if kept % 1000 == 0 { print("\(kept) samples, t=\(Int(t))s, \(Int(Date().timeIntervalSince(started)))s elapsed"); fflush(stdout) }
}
print("OK: \(kept) samples → \(args[2])")
