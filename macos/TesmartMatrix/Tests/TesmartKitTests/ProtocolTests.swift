import XCTest
@testable import TesmartKit

final class ProtocolTests: XCTestCase {
    func testCommands() {
        XCTAssertEqual(TesmartProtocol.routeCommand(input: 7, output: 3), "MT00SW0703NT")
        XCTAssertEqual(TesmartProtocol.allOutputsCommand(input: 2), "MT00SW0200NT")
        XCTAssertEqual(TesmartProtocol.loadPresetCommand(slot: 4), "MT00RD0104NT")
        XCTAssertEqual(TesmartProtocol.savePresetCommand(slot: 8), "MT00SV0008NT")
        XCTAssertEqual(TesmartProtocol.buzzerCommand(enabled: false), "MT00BZEN01NT")
    }

    func testParseRoutesLettersAndDigits() {
        let r = TesmartProtocol.parseRoutes("LINK:O1I1;O2I9;OAIG;OGI1;END")
        XCTAssertEqual(r, [1: 1, 2: 9, 10: 16, 16: 1])
    }

    func testParseTwoDigitInput() {
        XCTAssertEqual(TesmartProtocol.parseRoutes("O1I10;"), [1: 10])
    }

    func testParseEmpty() {
        XCTAssertTrue(TesmartProtocol.parseRoutes("").isEmpty)
    }
}
