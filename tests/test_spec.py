"""Spec-Driven Tests for ETP/1 (Specification v1.0).

These tests derive directly from:
- Section 3: Message Format
- Section 4: Message Types
- Section 7: File Names
- Section 8.1: Order of Checks
- Section 12: Worked Example
"""
import hashlib
import unittest
import sys
import os

# Ensure src/ is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

import etp


class TestETP1Specification(unittest.TestCase):

    # -------------------------------------------------------------------------
    # Section 7: File Names Invariants
    # -------------------------------------------------------------------------
    def test_section_7_valid_names(self):
        valid = [
            b"report-v2.pdf",
            b"a",
            b"Zulu.txt",
            b"x..y",
            b"a" * 64,  # max length 64
        ]
        for name in valid:
            with self.subTest(name=name):
                self.assertTrue(etp.valid_name(name), f"Expected {name} to be valid")

    def test_section_7_invalid_names(self):
        invalid = [
            b"../secret",     # directory traversal
            b"dir/file",      # slash not allowed
            b".hidden",       # begins with dot
            b".",             # dot
            b"..",            # dot dot
            b"my file.txt",   # space not allowed
            "résumé.txt".encode("utf-8"),  # non-ASCII not allowed
            b"",              # empty
            b"a" * 65,        # exceeds 64 bytes
            b"name\n",        # newline not allowed
        ]
        for name in invalid:
            with self.subTest(name=name):
                self.assertFalse(etp.valid_name(name), f"Expected {name} to be invalid")

    # -------------------------------------------------------------------------
    # Section 12: Worked Example Test Vectors (Exact Wire Format)
    # -------------------------------------------------------------------------
    def test_section_12_hello_encoding(self):
        # C->S HELLO 'eagle01'
        # 01 01 00 00 00 00 00 07 65 61 67 6c 65 30 31
        expected = bytes.fromhex("01 01 00 00 00 00 00 07 65 61 67 6c 65 30 31")
        actual = etp.encode(etp.HELLO, b"eagle01")
        self.assertEqual(actual, expected)

    def test_section_12_hello_ok_encoding(self):
        # S->C HELLO_OK 'ETP reference server 1.0' (24 bytes = 0x18)
        # 01 81 00 00 00 00 00 18 ...
        server_name = b"ETP reference server 1.0"
        expected = bytes.fromhex("01 81 00 00 00 00 00 18") + server_name
        actual = etp.encode(etp.HELLO_OK, server_name)
        self.assertEqual(actual, expected)

    def test_section_12_list_encoding(self):
        # C->S LIST
        # 01 02 00 00 00 00 00 00
        expected = bytes.fromhex("01 02 00 00 00 00 00 00")
        actual = etp.encode(etp.LIST)
        self.assertEqual(actual, expected)

    def test_section_12_get_encoding(self):
        # C->S GET 'alpha.txt'
        # 01 03 00 00 00 00 00 09 61 6c 70 68 61 2e 74 78 74
        expected = bytes.fromhex("01 03 00 00 00 00 00 09 61 6c 70 68 61 2e 74 78 74")
        actual = etp.encode(etp.GET, b"alpha.txt")
        self.assertEqual(actual, expected)

    def test_section_12_put_encoding(self):
        # C->S PUT 'notes.txt', payload 'Go Eagles!\n'
        # LENGTH 0x16 = 22 = 2 + 9 + 11. NAMELEN = 00 09.
        data = b"Go Eagles!\n"
        name = b"notes.txt"
        payload = len(name).to_bytes(2, "big") + name + data
        expected_hdr = bytes.fromhex("01 04 00 00 00 00 00 16")
        expected = expected_hdr + payload
        actual = etp.encode(etp.PUT, payload)
        self.assertEqual(actual, expected)

    def test_section_12_put_ok_digest(self):
        # S->C PUT_OK 32-byte SHA-256 digest
        data = b"Go Eagles!\n"
        digest = hashlib.sha256(data).digest()
        # From §12 table: 1c 94 1d ab 3d 13 2a 68 ee c1 32 13 8d 8d be 96 28 a2 5e 7d 2f 66 b7 bf
        expected_digest_prefix = bytes.fromhex("1c 94 1d ab 3d 13 2a 68")
        self.assertTrue(digest.startswith(expected_digest_prefix))
        expected = bytes.fromhex("01 84 00 00 00 00 00 20") + digest
        actual = etp.encode(etp.PUT_OK, digest)
        self.assertEqual(actual, expected)

    def test_section_12_bye_and_bye_ok_encoding(self):
        # C->S BYE: 01 05 00 00 00 00 00 00
        # S->C BYE_OK: 01 85 00 00 00 00 00 00
        self.assertEqual(etp.encode(etp.BYE), bytes.fromhex("01 05 00 00 00 00 00 00"))
        self.assertEqual(etp.encode(etp.BYE_OK), bytes.fromhex("01 85 00 00 00 00 00 00"))

    def test_section_12_error_encoding(self):
        # S->C ERROR NOT_FOUND (0x03), text 'no such file' (12 bytes = 0x0c)
        # 01 ff 03 00 00 00 00 0c 6e 6f 20 73 75 63 68 20 66 69 6c 65
        text = b"no such file"
        expected = bytes.fromhex("01 ff 03 00 00 00 00 0c") + text
        actual = etp.encode(etp.ERROR, text, status=etp.NOT_FOUND)
        self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
