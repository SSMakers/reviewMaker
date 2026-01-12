from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Dict, Any

VerifyResultType = Literal["confirm", "denied"]


@dataclass(frozen=True)
class VerifyConfirm:
    result: Literal["confirm"]
    contract_id: str
    remaining_days: int
    client_id: str
    secret_key: str
    mall_id: str
    redirect_url: str

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "VerifyConfirm":
        return VerifyConfirm(
            result="confirm",
            contract_id=str(d["contract_id"]),
            remaining_days=int(d["remaining_days"]),
            client_id=str(d["client_id"]),
            secret_key=str(d["secret_key"]),
            mall_id=str(d["mall_id"]),
            redirect_url=str(d["redirect_url"]),
        )


@dataclass(frozen=True)
class VerifyDenied:
    result: Literal["denied"]
    reason: str

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "VerifyDenied":
        return VerifyDenied(
            result="denied",
            reason=str(d.get("reason", "")),
        )


def parse_verify_response(d: Dict[str, Any]) -> VerifyConfirm | VerifyDenied:
    r = d.get("result")
    if r == "confirm":
        return VerifyConfirm.from_dict(d)
    if r == "denied":
        return VerifyDenied.from_dict(d)
    raise ValueError(f"Unknown verify result: {r} (payload={d})")
