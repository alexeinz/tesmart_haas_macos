"""Unit tests for the TESMart client (no Home Assistant required)."""
from __future__ import annotations

import asyncio
import importlib.util
import pathlib
import sys
import types

import unittest

ROOT = pathlib.Path(__file__).parent.parent / "custom_components" / "tesmart_matrix"

# Load client.py standalone, stubbing the package-relative LOGGER import.
pkg = types.ModuleType("tm")
pkg.__path__ = [str(ROOT)]
sys.modules["tm"] = pkg
const = types.ModuleType("tm.const")
import logging  # noqa: E402

const.LOGGER = logging.getLogger("tm")
sys.modules["tm.const"] = const
spec = importlib.util.spec_from_file_location("tm.client", ROOT / "client.py")
client_mod = importlib.util.module_from_spec(spec)
sys.modules["tm.client"] = client_mod
spec.loader.exec_module(client_mod)

Client = client_mod.TesmartLanClient
ClientError = client_mod.TesmartLanClientError
CommError = client_mod.TesmartLanClientCommunicationError


class ParseTests(unittest.TestCase):
    def test_letters_and_digits(self):
        routes = Client._parse_routes("LINK:O1I1;O2I3;OAIG;OGIA;END")
        self.assertEqual(routes, {1: 1, 2: 3, 10: 16, 16: 10})

    def test_two_digit_input_not_truncated(self):
        self.assertEqual(Client._parse_routes("O1I10")[1], 10)

    def test_empty(self):
        self.assertEqual(Client._parse_routes("garbage"), {})


class FakeDevice:
    """Tiny TCP server recording commands and replying with a canned payload."""

    def __init__(self, reply: bytes = b"", delay: float = 0.0):
        self.reply, self.delay = reply, delay
        self.commands: list[bytes] = []
        self.active = 0
        self.max_active = 0

    async def handle(self, reader, writer):
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        self.commands.append(await reader.read(256))
        await asyncio.sleep(self.delay)
        if self.reply:
            writer.write(self.reply)
            await writer.drain()
        writer.close()
        self.active -= 1


class ClientTests(unittest.IsolatedAsyncioTestCase):
    async def _serve(self, device):
        server = await asyncio.start_server(device.handle, "127.0.0.1", 0)
        self.addAsyncCleanup(self._close, server)
        return server.sockets[0].getsockname()[1]

    @staticmethod
    async def _close(server):
        server.close()
        await server.wait_closed()

    async def test_set_route_command_format(self):
        dev = FakeDevice()
        port = await self._serve(dev)
        await Client("127.0.0.1", port).set_route(output=3, input_port=7)
        await asyncio.sleep(0.1)  # fire-and-forget: let the server record it
        self.assertEqual(dev.commands, [b"MT00SW0703NT\r\n"])

    async def test_get_routes_complete(self):
        reply = b"LINK:" + b"".join(f"O{o}I{o};".encode() for o in range(1, 10)) + b"END"
        port = await self._serve(FakeDevice(reply))
        routes = await Client("127.0.0.1", port).get_routes(expected_outputs=9)
        self.assertEqual(len(routes), 9)

    async def test_get_routes_incomplete_raises(self):
        port = await self._serve(FakeDevice(b"O1I1;O2I2;END"))
        with self.assertRaisesRegex(ClientError, "Incomplete"):
            await Client("127.0.0.1", port).get_routes(expected_outputs=16)

    async def test_commands_are_serialized(self):
        dev = FakeDevice(reply=b"O1I1;END", delay=0.05)
        port = await self._serve(dev)
        c = Client("127.0.0.1", port)
        await asyncio.gather(*(c.get_routes() for _ in range(4)))
        self.assertEqual(len(dev.commands), 4)
        self.assertEqual(dev.max_active, 1)

    async def test_connection_refused_is_comm_error(self):
        with self.assertRaises(CommError):
            await Client("127.0.0.1", 1, timeout=0.5).set_route(1, 1)

    async def test_preset_bounds(self):
        c = Client("127.0.0.1", 1)
        with self.assertRaises(ClientError):
            await c.load_preset(9)
        with self.assertRaises(ClientError):
            await c.save_preset(0)


if __name__ == "__main__":
    unittest.main()
