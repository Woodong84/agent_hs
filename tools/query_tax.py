"""관세율 조회 Tool. UNI-PASS API 키 미설정 시 정적 Fallback 세율표 사용."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain.tools import tool
from configs.settings import settings

# 정적 Fallback 세율표 (주요 반도체 관련 류 기준)
_STATIC_TAX_TABLE: dict = {
    "28": {
        "basic_rate": "6.5%",
        "fta_rates": [
            {"country": "미국", "agreement": "한-미 FTA", "rate": "0%"},
            {"country": "EU", "agreement": "한-EU FTA", "rate": "0%"},
            {"country": "중국", "agreement": "한-중 FTA", "rate": "확인필요"},
        ],
        "import_requirements": "화학물질관리법·위험물 규정 확인 필요",
    },
    "38": {
        "basic_rate": "6.5%",
        "fta_rates": [
            {"country": "미국", "agreement": "한-미 FTA", "rate": "0%"},
            {"country": "EU", "agreement": "한-EU FTA", "rate": "0%"},
            {"country": "중국", "agreement": "한-중 FTA", "rate": "확인필요"},
        ],
        "import_requirements": "화학물질 안전관리법 준수 필요",
    },
    "39": {
        "basic_rate": "8%",
        "fta_rates": [
            {"country": "미국", "agreement": "한-미 FTA", "rate": "0%"},
            {"country": "EU", "agreement": "한-EU FTA", "rate": "0%"},
            {"country": "중국", "agreement": "한-중 FTA", "rate": "확인필요"},
        ],
        "import_requirements": "특별한 수입 요건 없음",
    },
    "84": {
        "basic_rate": "0%",
        "fta_rates": [
            {"country": "미국", "agreement": "한-미 FTA", "rate": "0%"},
            {"country": "EU", "agreement": "한-EU FTA", "rate": "0%"},
            {"country": "중국", "agreement": "한-중 FTA", "rate": "0%"},
        ],
        "import_requirements": "반도체 제조 장비 면세 적용",
    },
    "85": {
        "basic_rate": "0%",
        "fta_rates": [
            {"country": "미국", "agreement": "한-미 FTA", "rate": "0%"},
            {"country": "EU", "agreement": "한-EU FTA", "rate": "0%"},
            {"country": "중국", "agreement": "한-중 FTA", "rate": "0%"},
        ],
        "import_requirements": "반도체 부품 면세",
    },
    "38": {
        "basic_rate": "6.5%",
        "fta_rates": [
            {"country": "미국", "agreement": "한-미 FTA", "rate": "0%"},
            {"country": "EU", "agreement": "한-EU FTA", "rate": "0%"},
            {"country": "중국", "agreement": "한-중 FTA", "rate": "확인필요"},
        ],
        "import_requirements": "화학물질 안전관리법 준수 필요",
    },
    "76": {
        "basic_rate": "8%",
        "fta_rates": [
            {"country": "미국", "agreement": "한-미 FTA", "rate": "0%"},
            {"country": "EU", "agreement": "한-EU FTA", "rate": "0%"},
            {"country": "중국", "agreement": "한-중 FTA", "rate": "확인필요"},
        ],
        "import_requirements": "특별한 수입 요건 없음",
    },
    "90": {
        "basic_rate": "0%",
        "fta_rates": [
            {"country": "미국", "agreement": "한-미 FTA", "rate": "0%"},
            {"country": "EU", "agreement": "한-EU FTA", "rate": "0%"},
            {"country": "중국", "agreement": "한-중 FTA", "rate": "0%"},
        ],
        "import_requirements": "광학기기 면세",
    },
}

# 수출 시 목적국 기준 관세율 (한국 수출 → 목적국 수입세율)
_STATIC_EXPORT_TABLE: dict = {
    "28": {
        "US": {"basic_rate": "3.7%", "fta_rate": "0% (한-미 FTA)"},
        "CN": {"basic_rate": "6.5%", "fta_rate": "확인필요 (한-중 FTA)"},
    },
    "38": {
        "US": {"basic_rate": "3.7%", "fta_rate": "0% (한-미 FTA)"},
        "CN": {"basic_rate": "6.5%", "fta_rate": "확인필요 (한-중 FTA)"},
    },
    "39": {
        "US": {"basic_rate": "3.7%", "fta_rate": "0% (한-미 FTA)"},
        "CN": {"basic_rate": "6.5%", "fta_rate": "확인필요 (한-중 FTA)"},
    },
    "84": {
        "US": {"basic_rate": "0%", "fta_rate": "0% (한-미 FTA)"},
        "CN": {"basic_rate": "0%", "fta_rate": "0% (한-중 FTA)"},
    },
    "85": {
        "US": {"basic_rate": "0%", "fta_rate": "0% (한-미 FTA)"},
        "CN": {"basic_rate": "0%", "fta_rate": "0% (한-중 FTA)"},
    },
    "90": {
        "US": {"basic_rate": "0%", "fta_rate": "0% (한-미 FTA)"},
        "CN": {"basic_rate": "0%", "fta_rate": "0% (한-중 FTA)"},
    },
}

_DEFAULT_TAX = {
    "basic_rate": "확인필요",
    "fta_rates": [
        {"country": "미국", "agreement": "한-미 FTA", "rate": "확인필요"},
        {"country": "EU", "agreement": "한-EU FTA", "rate": "확인필요"},
        {"country": "중국", "agreement": "한-중 FTA", "rate": "확인필요"},
    ],
    "import_requirements": "관세청 UNI-PASS에서 확인 필요",
}


def _fallback_rate(hs_code: str, trade_direction: str = "", target_country: str = "") -> dict:
    hs_class = hs_code[:2] if len(hs_code) >= 2 else ""

    if "수출" in trade_direction:
        country_key = "CN" if "중국" in target_country else "US"
        export_entry = _STATIC_EXPORT_TABLE.get(hs_class, {}).get(country_key)
        if export_entry:
            country_name = "중국" if country_key == "CN" else "미국"
            agreement = "한-중 FTA" if country_key == "CN" else "한-미 FTA"
            return {
                "hs_code": hs_code,
                "basic_rate": export_entry["basic_rate"],
                "fta_rates": [{"country": country_name, "agreement": agreement,
                               "rate": export_entry["fta_rate"]}],
                "import_requirements": f"수출 목적국({country_name}) 통관 요건 확인 필요",
                "is_fallback": True,
                "rate_basis": f"{country_name} 수입 기준 관세율",
            }

    table_entry = _STATIC_TAX_TABLE.get(hs_class, _DEFAULT_TAX)
    return {
        "hs_code": hs_code,
        "basic_rate": table_entry["basic_rate"],
        "fta_rates": table_entry["fta_rates"],
        "import_requirements": table_entry["import_requirements"],
        "is_fallback": True,
    }


@tool
def query_tax_rate(
    hs_code: str,
    trade_direction: str,
    target_country: str = "",
) -> dict:
    """HS-Code의 관세율을 조회한다. API 키 미설정 시 정적 세율표를 반환한다."""
    if not settings.UNIPASS_API_KEY:
        return _fallback_rate(hs_code, trade_direction, target_country)

    import requests

    params = {
        "customsUniqueNo": settings.UNIPASS_API_KEY,
        "hsSgn": hs_code,
        "natCd": target_country or "US",
    }
    try:
        resp = requests.get(
            "https://unipass.customs.go.kr/csp/apt.do",
            params=params,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

        basic_rate = data.get("basicRate", "확인필요")
        fta_rates = []
        for item in data.get("ftaList", []):
            fta_rates.append({
                "country": item.get("natNm", ""),
                "agreement": item.get("ftaNm", ""),
                "rate": item.get("ftaRate", "확인필요"),
            })

        return {
            "hs_code": hs_code,
            "basic_rate": basic_rate,
            "fta_rates": fta_rates,
            "import_requirements": data.get("impReq", "특별한 수입 요건 없음"),
            "is_fallback": False,
        }
    except Exception:
        return _fallback_rate(hs_code)
