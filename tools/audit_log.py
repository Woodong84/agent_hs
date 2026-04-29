"""감사 로그 저장 Tool. 1순위 외 코드 선택 시 수정 사유 필수."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import uuid
from datetime import datetime
from pathlib import Path
from langchain.tools import tool
from configs.settings import settings


@tool
def save_audit_log(
    audit_log: dict,
    user_selection: str,
    modify_reason: str = "",
) -> dict:
    """Agent 처리 결과를 감사 로그로 저장한다."""
    candidates = audit_log.get("candidates", [])
    top1_code = candidates[0]["hs_code"] if candidates else ""

    if top1_code and user_selection != top1_code and not modify_reason.strip():
        return {
            "log_id": None,
            "saved": False,
            "file_path": None,
            "error": "수정 사유 미입력: 1순위 외 코드 선택 시 수정 사유 필수",
        }

    log_id = str(uuid.uuid4())
    entry = {
        "log_id": log_id,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "user_selection": user_selection,
        "top1_recommendation": top1_code,
        "modify_reason": modify_reason,
        "final_hs_code": user_selection,
        **audit_log,
    }

    log_path = Path(settings.AUDIT_LOG_PATH)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return {
        "log_id": log_id,
        "saved": True,
        "file_path": str(log_path),
        "error": None,
    }
