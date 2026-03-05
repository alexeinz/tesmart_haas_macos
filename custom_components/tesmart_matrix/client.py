"""Async TCP client for TESMart LAN matrix switches."""
from __future__ import annotations

import asyncio
import re

from .const import LOGGER

_ROUTE_PATTERN = re.compile(r"O([1-9A-G]|1[0-6])I([1-9A-G]|1[0-6])")


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

    async def get_routes(self) -> dict[int, int]:
        """Read full output->input route map."""
        # Some devices return route data in partial chunks; retry a few times
        # before failing the config flow or coordinator refresh.
        for _attempt in range(3):
            response = await self._send_command("MT00RD0000NT", expect_response=True)
            routes = self._parse_routes(response)
            if routes:
                return routes
            await asyncio.sleep(0.2)
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
        writer: asyncio.StreamWriter | None = None
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self._host, self._port),
                timeout=self._timeout,
            )
            writer.write(f"{command}\r\n".encode())
            await asyncio.wait_for(writer.drain(), timeout=self._timeout)

            response = ""
            if expect_response:
                chunks: list[bytes] = []
                while True:
                    try:
                        data = await asyncio.wait_for(reader.read(4096), timeout=self._timeout)
                    except TimeoutError:
                        # Device may keep socket open; treat read timeout as end of response.
                        break
                    if not data:
                        break
                    chunks.append(data)
                    # Typical route payload contains END; stop early once seen.
                    if b"END" in b"".join(chunks):
                        break
                response = b"".join(chunks).decode(errors="ignore")
            return response
        except (TimeoutError, OSError) as err:
            raise TesmartLanClientCommunicationError(
                f"Failed talking to {self._host}:{self._port}: {err}"
            ) from err
        finally:
            if writer is not None:
                writer.close()
                await writer.wait_closed()

    async def _send_hex(self, payload: bytes) -> None:
        """Send raw hex payload to the device."""
        writer: asyncio.StreamWriter | None = None
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(self._host, self._port),
                timeout=self._timeout,
            )
            writer.write(payload)
            await asyncio.wait_for(writer.drain(), timeout=self._timeout)
        except (TimeoutError, OSError) as err:
            raise TesmartLanClientCommunicationError(
                f"Failed talking to {self._host}:{self._port}: {err}"
            ) from err
        finally:
            if writer is not None:
                writer.close()
                await writer.wait_closed()

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
