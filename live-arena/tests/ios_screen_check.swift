// Hosted macOS-only initial-screen check. OCR is not an interaction or device test.
import Foundation
import Vision

guard CommandLine.arguments.count == 2 else {
    fatalError("Expected one simulator screenshot path")
}
let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.recognitionLanguages = ["en-US"]
request.usesLanguageCorrection = false
let handler = VNImageRequestHandler(url: URL(fileURLWithPath: CommandLine.arguments[1]), options: [:])
try handler.perform([request])
let lines = (request.results ?? []).compactMap { $0.topCandidates(1).first?.string }
let output = try JSONSerialization.data(withJSONObject: ["recognizedText": lines], options: [.sortedKeys])
print(String(data: output, encoding: .utf8)!)
let normalized = lines.joined().lowercased().filter { $0.isLetter || $0.isNumber }
guard normalized.contains("builderwars"),
      normalized.contains("youragentyourarena") || normalized.contains("quickmatch") else {
    fputs("BuilderWars initial-screen text not found. Rendering gate failed.\n", stderr)
    exit(1)
}
