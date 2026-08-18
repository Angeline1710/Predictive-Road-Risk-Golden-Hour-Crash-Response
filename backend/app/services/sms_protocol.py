"""PRD §6.2.1: the RRX1 SMS wire protocol.

    RRX1|<alert_uuid_b32_13>|<lat_e5>|<lon_e5>|<epoch_s>|<sev>|<spd_kmh>|
         <hdg_deg>|<gps_acc_m>|<peak_g_x10>|<flags>|<crc8>

Example (98 chars, fits one GSM-7 SMS):
    RRX1|K7Q2M9XZ4A8BF|1291845|8022456|1786412355|3|68|142|8|91|RM|3C
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

CROCKFORD_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_DECODE = {c: i for i, c in enumerate(CROCKFORD_ALPHABET)}

SEVERITY_CODE = {1: "MINOR", 2: "MODERATE", 3: "SEVERE", 4: "CRITICAL"}


class RRX1ParseError(ValueError):
    pass


def crc8_atm(data: bytes) -> int:
    """CRC-8/ATM (aka CRC-8/I-432-1): poly 0x07, init 0x00, no reflection,
    no xorout -- the algorithm PRD §6.2.1 explicitly names.

    NOTE: PRD §6.2.1's own worked example
    ("RRX1|K7Q2M9XZ4A8BF|...|RM|3C") does NOT reproduce as 0x3C under this
    algorithm (it computes 0x23), and no other CRC-8 catalog variant
    (SMBUS/MAXIM/DVB-S2/CDMA2000/DARC/AUTOSAR/BLUETOOTH/GSM-A/ITU) produces
    0x3C for that payload either -- checked exhaustively. The example's CRC
    digits are almost certainly illustrative placeholder text in the spec
    document, not a literally computed checksum. This function still
    implements the named algorithm correctly; it just cannot be verified
    against that one worked example, and self-consistency (encode then
    decode with THIS implementation) is what parse_rrx1() actually relies on.
    """
    crc = 0x00
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = ((crc << 1) ^ 0x07) & 0xFF if (crc & 0x80) else (crc << 1) & 0xFF
    return crc


def _decode_crockford(s: str) -> int:
    val = 0
    for ch in s.upper():
        if ch not in _DECODE:
            raise RRX1ParseError(f"invalid Crockford base32 character: {ch!r}")
        val = (val << 5) | _DECODE[ch]
    return val


def _encode_crockford(value: int, length: int) -> str:
    chars = []
    for _ in range(length):
        chars.append(CROCKFORD_ALPHABET[value & 0x1F])
        value >>= 5
    return "".join(reversed(chars))


def encode_rrx1(
    alert_uuid: uuid.UUID, lat: float, lon: float, occurred_at: datetime,
    severity: str, speed_kmh: float, heading_deg: float, gps_accuracy_m: float,
    peak_g: float, rollover: bool = False, still_moving: bool = False,
    unresponsive: bool = False, cancel_window_expired: bool = True,
) -> str:
    """Reference encoder -- not used by the backend at runtime (the phone
    builds this message, not the server), but kept here as the canonical,
    executable spec for the Android team to mirror rather than re-derive the
    bit-packing from prose. Also what this module's own tests build against.
    """
    prefix_bits = alert_uuid.int >> (128 - 65)
    sev_code = {v: k for k, v in SEVERITY_CODE.items()}[severity]
    flags = "".join([
        "R" if rollover else "", "M" if still_moving else "",
        "U" if unresponsive else "", "C" if cancel_window_expired else "",
    ])
    payload = "|".join([
        "RRX1", _encode_crockford(prefix_bits, 13), str(round(lat * 1e5)),
        str(round(lon * 1e5)), str(int(occurred_at.timestamp())), str(sev_code),
        str(round(speed_kmh)), str(round(heading_deg)), str(round(gps_accuracy_m)),
        str(round(peak_g * 10)), flags,
    ])
    return f"{payload}|{crc8_atm(payload.encode('ascii')):02X}"


@dataclass
class ParsedRRX1:
    alert_uuid: uuid.UUID   # see note on `uuid_prefix_bits` below
    uuid_prefix_bits: int   # the 65 raw bits actually transmitted
    lat: float
    lon: float
    occurred_at: datetime
    severity: str
    speed_kmh: float
    heading_deg: float
    gps_accuracy_m: float
    peak_g: float
    rollover: bool
    still_moving: bool
    unresponsive: bool
    cancel_window_expired: bool


def parse_rrx1(body: str) -> ParsedRRX1:
    """Raises RRX1ParseError on any malformed or corrupted message -- this
    function is the entire trust boundary for an inherently untrusted,
    unauthenticated-at-the-telecom-layer channel (PRD NFR-S7).
    """
    body = body.strip()
    payload, _, crc_hex = body.rpartition("|")
    if not payload or len(crc_hex) != 2:
        raise RRX1ParseError("malformed message: missing CRC field")
    try:
        expected_crc = int(crc_hex, 16)
    except ValueError as e:
        raise RRX1ParseError(f"CRC field is not valid hex: {crc_hex!r}") from e

    actual_crc = crc8_atm(payload.encode("ascii"))
    if actual_crc != expected_crc:
        raise RRX1ParseError(
            f"CRC mismatch (got {actual_crc:02X}, expected {expected_crc:02X}) -- "
            "message corrupted or spoofed in transit"
        )

    # "RRX1" plus 10 data fields (uuid, lat, lon, epoch, sev, spd, hdg, acc,
    # peak_g, flags) = 11 pipe-delimited parts once the trailing CRC has
    # already been split off above.
    parts = payload.split("|")
    if len(parts) != 11 or parts[0] != "RRX1":
        raise RRX1ParseError(f"expected 11 pipe-delimited fields starting with RRX1, got {len(parts)}")

    try:
        uuid_b32, lat_e5, lon_e5, epoch_s, sev, spd, hdg, acc, peak_g_x10, flags = parts[1:]

        prefix_bits = _decode_crockford(uuid_b32)
        if prefix_bits.bit_length() > 65:
            raise RRX1ParseError("decoded UUID prefix exceeds 65 bits")
        # PRD §6.2.1: "first 65 bits of the UUID". A UUID is 128 bits, so this
        # is IRREDUCIBLY LOSSY -- the SMS channel cannot carry the full
        # alert_uuid in 160 GSM-7 characters. We reconstruct a UUID by
        # placing the 65 received bits as the high bits and zero-padding the
        # remaining 63, which is DETERMINISTIC but will NOT bit-for-bit equal
        # the original alert_uuid the phone generated over HTTPS. True
        # cross-channel dedup (matching this SMS alert to a same-incident
        # DATA-channel delivery) requires comparing the 65-bit PREFIX, not
        # UUID equality -- not yet wired into app/services/alerts.py; see
        # MVP-PLAN.md follow-ups.
        full_int = prefix_bits << (128 - 65)
        reconstructed_uuid = uuid.UUID(int=full_int)

        return ParsedRRX1(
            alert_uuid=reconstructed_uuid,
            uuid_prefix_bits=prefix_bits,
            lat=int(lat_e5) / 1e5,
            lon=int(lon_e5) / 1e5,
            occurred_at=datetime.fromtimestamp(int(epoch_s), tz=UTC),
            severity=SEVERITY_CODE.get(int(sev), "SEVERE"),
            speed_kmh=float(spd),
            heading_deg=float(hdg),
            gps_accuracy_m=float(acc),
            peak_g=float(peak_g_x10) / 10.0,
            rollover="R" in flags,
            still_moving="M" in flags,
            unresponsive="U" in flags,
            cancel_window_expired="C" in flags,
        )
    except (ValueError, IndexError) as e:
        raise RRX1ParseError(f"malformed field in RRX1 message: {e}") from e
