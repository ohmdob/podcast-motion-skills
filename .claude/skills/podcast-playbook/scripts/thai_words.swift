// Thai word boundaries from the system's dictionary: JSON array of strings on stdin → JSON array of arrays of words on stdout.
//   swiftc -O scripts/thai_words.swift -o /tmp/thai_words
import Foundation

let input = FileHandle.standardInput.readDataToEndOfFile()
guard let lines = try? JSONSerialization.jsonObject(with: input) as? [String] else { print("[]"); exit(1) }
var out: [[String]] = []
for line in lines {
    var words: [String] = []
    let s = line as NSString
    s.enumerateSubstrings(in: NSRange(location: 0, length: s.length), options: [.byWords, .localized]) { w, _, _, _ in
        if let w = w { words.append(w) }
    }
    out.append(words)
}
FileHandle.standardOutput.write(try! JSONSerialization.data(withJSONObject: out))
