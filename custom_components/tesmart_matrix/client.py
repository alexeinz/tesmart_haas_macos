"""Async TCP client for TESMart LAN matrix switches."""
from __future__ import annotations

import asyncio
import re

from .const import LOGGER

_ROUTE_PATTERN = re.compile(r"O(1[0-6]|[1-9A-G])I(1[0-6]|[1-9A-G])")


class TesmartLanClientError(Exception):
    """Base TESMart client error."""


class TesmartLanClientCommunicationError(TesmartLanClientError):
    """Communication error with TESMart device."""


class TesmartLanClient:
    """Simple TCP client for TESMart matrix ASCII protocol."""

    def __init__(self, host: str, port: int, timeout: float = 3.0) -> None:
        """Initialize client."""
        self._host = host
        self._port = port
        self._timeout = timeout
        # The device handles one connection at a time; serialize all access.
        self._lock = asyncio.Lock()

    async def get_routes(self, expected_outputs: int | None = None) -> dict[int, int]:
        """Read full output->input route map.

        When ``expected_outputs`` is given, partial answers (fewer outputs than
        expected) are retried instead of being returned.
        """
        # Some devices return route data in partial chunks; retry a few times
        # before failing the config flow or coordinator refresh.
        routes: dict[int, int] = {}
        for _attempt in range(3):
            response = await self._send_command("MT00RD0000NT", expect_response=True)
            routes = self._parse_routes(response)
            if routes and (expected_outputs is None or len(routes) >= expected_outputs):
                return routes
            await asyncio.sleep(0.2)
        if routes:
            raise TesmartLanClientError(
                f"Incomplete route data from {self._host}:{self._port}: "
                f"got {len(routes)} of {expected_outputs} outputs"
            )
        raise TesmartLanClientError(
            f"No route data received from {self._host}:{self._port}"
        )

    async def set_route(self, output: int, input_port: int) -> None:
        """Route one output to one input."""
        await self._send_command(f"MT00SW{input_port:02d}{output:02d}NT")

    async def set_all_outputs(self, input_port: int) -> None:
        """Route all outputs to one input."""
        await self._send_command(f"MT00SW{input_port:02d}00NT")

    async def mirror_outputs(self) -> None:
        """Mirror outputs (1->1, 2->2, ...)."""
        await self._send_command("MT00SW0000NT")

    async def load_preset(self, slot: int) -> None:
        """Load preset slot (01-08)."""
        if not 1 <= slot <= 8:
            raise TesmartLanClientError(f"Invalid preset slot '{slot}', expected 1-8.")
        await self._send_command(f"MT00RD01{slot:02d}NT")

    async def save_preset(self, slot: int) -> None:
        """Save current routes to preset slot (01-08)."""
        if not 1 <= slot <= 8:
            raise TesmartLanClientError(f"Invalid preset slot '{slot}', expected 1-8.")
        await self._send_command(f"MT00SV00{slot:02d}NT")

    async def set_buzzer_enabled(self, enabled: bool) -> None:
        """Enable or disable buzzer sounds."""
        command = "MT00BZEN00NT" if enabled else "MT00BZEN01NT"
        await self._send_command(command)

    async def set_led_timeout_seconds(self, timeout_seconds: int) -> None:
        """Set LED timeout in seconds (supported values: 0, 10, 30)."""
        if timeout_seconds not in {0, 10, 30}:
            raise TesmartLanClientError(
                f"Unsupported LED timeout '{timeout_seconds}'. Use 0, 10, or 30."
            )
        await self._send_hex(bytes([0xAA, 0xBB, 0x03, 0x03, timeout_seconds, 0xEE]))

    async def set_auto_input_detection(self, enabled: bool) -> None:
        """Enable/disable auto input detection (experimental command mapping)."""
        value = 0x01 if enabled else 0x00
        await self._send_hex(bytes([0xAA, 0xBB, 0x03, 0x04, value, 0xEE]))

    async def set_fan_mode(self, mode: str) -> None:
        """Set fan mode (experimental command mapping)."""
        mapping = {
            "Auto": 0x00,
            "Low": 0x01,
            "High": 0x02,
        }
        if mode not in mapping:
            raise TesmartLanClientError(f"Unsupported fan mode '{mode}'")
        await self._send_hex(bytes([0xAA, 0xBB, 0x03, 0x05, mapping[mode], 0xEE]))

    async def _send_command(self, command: str, expect_response: bool = False) -> str:
        """Send one command and optionally read response."""
        return await self._transact(f"{command}\r\n".encode(), expect_response)

    async def _send_hex(self, payload: bytes) -> None:
        """Send raw hex payload to the device."""
        await self._transact(payload, False)

    async def _transact(self, payload: bytes, expect_response: bool) -> str:
        """Open a connection, send payload, optionally read the reply."""
        async with self._lock:
            writer: asyncio.StreamWriter | None = None
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(self._host, self._port),
                    timeout=self._timeout,
                )
                writer.write(payload)
                await asyncio.wait_for(writer.drain(), timeout=self._timeout)
                if not expect_response:
                    return ""
                return await self._read_response(reader)
            except (TimeoutError, OSError) as err:
                raise TesmartLanClientCommunicationError(
                    f"Failed talking to {self._host}:{self._port}: {err}"
                ) from err
            finally:
                await self._close(writer)

    async def _read_response(self, reader: asyncio.StreamReader) -> str:
        """Read until END marker, EOF, or read timeout."""
        buffer = b""
        while True:
            try:
                data = await asyncio.wait_for(reader.read(4096), timeout=self._timeout)
            except TimeoutError:
                # Device may keep socket open; treat read timeout as end of response.
                break
            if not data:
                break
            buffer += data
            # Typical route payload contains END; stop early once seen.
            if b"END" in buffer:
                break
        return buffer.decode(errors="ignore")

    @staticmethod
    async def _close(writer: asyncio.StreamWriter | None) -> None:
        """Close a writer, ignoring errors raised during teardown."""
        if writer is None:
            return
        writer.close()
        try:
            await asyncio.wait_for(writer.wait_closed(), timeout=2)
        except (TimeoutError, OSError):
            LOGGER.debug("Error while closing connection", exc_info=True)

    @staticmethod
    def _parse_routes(raw: str) -> dict[int, int]:
        """Parse routing response like LINK:O1I1;OAIG;...;END."""
        routes: dict[int, int] = {}
        for output, input_port in _ROUTE_PATTERN.findall(raw):
            try:
                routes[TesmartLanClient._decode_port(output)] = TesmartLanClient._decode_port(
                    input_port
                )
            except ValueError:
                LOGGER.debug("Skipping invalid route token: O%sI%s", output, input_port)
        return routes

    @staticmethod
    def _decode_port(token: str) -> int:
        """Decode protocol token (1-9,A-G) into integer port number."""
        if token.isdigit():
            return int(token)
        return 10 + ord(token.upper()) - ord("A")
