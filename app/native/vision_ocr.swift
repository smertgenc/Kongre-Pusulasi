import Foundation
import Vision
import ImageIO

func finish(_ value: [String: Any], _ code: Int32 = 0) -> Never {
    let data = try! JSONSerialization.data(withJSONObject: value, options: [.sortedKeys])
    FileHandle.standardOutput.write(data)
    exit(code)
}
guard CommandLine.arguments.count == 2 else { finish(["error":"INVALID_IMAGE"], 2) }
let url = URL(fileURLWithPath: CommandLine.arguments[1])
guard let source = CGImageSourceCreateWithURL(url as CFURL, nil),
      CGImageSourceGetCount(source) == 1,
      let properties = CGImageSourceCopyPropertiesAtIndex(source, 0, nil) as? [CFString: Any],
      let width = properties[kCGImagePropertyPixelWidth] as? Int,
      let height = properties[kCGImagePropertyPixelHeight] as? Int else { finish(["error":"INVALID_IMAGE"], 2) }
guard width > 0 && height > 0 && width <= 12000 && height <= 12000 && width * height <= 20_000_000 else {
    finish(["error":"IMAGE_TOO_LARGE"], 2)
}
let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.usesLanguageCorrection = true
request.automaticallyDetectsLanguage = true
do {
    let supported = try request.supportedRecognitionLanguages()
    let preferred = ["tr-TR", "en-US"].filter { supported.contains($0) }
    if !preferred.isEmpty { request.recognitionLanguages = preferred }
    try VNImageRequestHandler(url: url, options: [:]).perform([request])
    let lines = (request.results ?? []).compactMap { observation -> [String: Any]? in
        guard let candidate = observation.topCandidates(1).first else { return nil }
        return ["text":candidate.string, "confidence":Double(candidate.confidence),
                "box":[observation.boundingBox.origin.x, observation.boundingBox.origin.y,
                       observation.boundingBox.width, observation.boundingBox.height]]
    }
    let text = lines.compactMap { $0["text"] as? String }.joined(separator:"\n")
    guard text.count <= 60_000 else { finish(["error":"TEXT_TOO_LARGE"], 2) }
    finish(["text":text,"lines":lines,"width":width,"height":height,"engine":"Apple Vision"])
} catch { finish(["error":"OCR_FAILED"], 2) }
