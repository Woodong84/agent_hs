"""
HS 표준해석 지침 PDF 텍스트 파일 파싱 → Pinecone 적재용 TXT 청크 생성
입력: hs_standard_text.txt (pypdf 추출본)
출력: data/raw/hs_std_XXXX.txt (기존 ingest 포맷)
"""
import re
from pathlib import Path
from collections import Counter

SRC = Path("/root/.claude/uploads/0afa44bd-8870-4d62-986d-09dbd7af90dc/68fc1f9d-hs_standard_text.txt")
OUT_DIR = Path("/home/user/agent_hs/data/raw")
PUB_YEAR = "2023"

# HS 코드 패턴: 8486.10-2000 형태
HS_CODE_RE = re.compile(r'(\d{4}[.\-]\d{2}[.\-]\d{4})')
DATE_RE    = re.compile(r'(\d{4}-\d{2}-\d{2})')
# 장(章) 헤더
CHAPTER_RE = re.compile(r'제(\d+)장\s*[lLl:：]?\s*(.+)')

def normalize_hs(raw: str) -> str:
    return re.sub(r'[^\d]', '', raw)[:10]

def safe_fname(s: str) -> str:
    s = re.sub(r'[^\w가-힣a-zA-Z0-9_-]', '_', s)
    return re.sub(r'_+', '_', s).strip('_')[:40]


def parse(text: str) -> list[dict]:
    """페이지 단위로 분리 후 엔트리 추출."""
    pages = re.split(r'=== PAGE \d+ ===\n?', text)

    entries = []
    chapter_num  = 0
    chapter_name = ""

    # 실제 내용은 15페이지 이후부터 시작 (1-14는 목차/일러두기)
    CONTENT_START = 15

    for pi, page in enumerate(pages):
        if pi < CONTENT_START:
            # 목차 구간: 장 이름만 캐치
            cm = CHAPTER_RE.search(page)
            if cm:
                chapter_num  = int(cm.group(1))
                chapter_name = cm.group(2).strip()
            continue

        # 장 헤더 업데이트
        cm = CHAPTER_RE.search(page)
        if cm:
            chapter_num  = int(cm.group(1))
            chapter_name = cm.group(2).strip()

        lines = page.split('\n')

        # 엔트리 헤더: "N. 한글명 (English Name)" 패턴
        # 영문명이 포함된 줄(ASCII 단어 포함)만 엔트리로 인식
        ENTRY_LINE = re.compile(
            r'^(\d+)\.\s+([\w가-힣\s\-\.]+?)\s*\(([A-Za-z][^\)]{3,})\)\s*$'
        )

        for li, line in enumerate(lines):
            m = ENTRY_LINE.match(line.strip())
            if not m:
                continue

            entry_num = m.group(1)
            product_ko = m.group(2).strip()
            product_en = m.group(3).strip()

            # 노이즈 제목 필터 (물품설명, 결정사유 등)
            if product_ko in {"물품설명", "결정사유", "구성요소별 기능",
                               "용도", "개요", "작동원리", "공정"}:
                continue
            # 영문이 단순 약어(두 글자 이하) → 노이즈
            if len(product_en.split()) <= 1 and len(product_en) <= 4:
                continue

            # 이후 10줄 내에서 HS 코드 탐색
            window = '\n'.join(lines[li:min(li+12, len(lines))])
            # 다음 페이지 앞부분도 포함
            if pi + 1 < len(pages):
                window += '\n' + pages[pi+1][:400]

            hs_matches = HS_CODE_RE.findall(window)
            hs_raw = hs_matches[0] if hs_matches else ""
            hs_code = normalize_hs(hs_raw) if hs_raw else ""

            # 시행일자
            date_m = DATE_RE.search(window)
            enacted = date_m.group(1) if date_m else ""

            # 본문 수집: 현재 페이지 나머지 + 다음 1-3 페이지
            body_parts = ['\n'.join(lines[:li])]   # 현재 페이지 앞부분(설명)
            for npi in range(pi+1, min(pi+4, len(pages))):
                np = pages[npi]
                # 다음 엔트리 헤더가 나타나면 그 앞까지만
                stop_m = ENTRY_LINE.search(np)
                if stop_m:
                    body_parts.append(np[:stop_m.start()])
                    break
                body_parts.append(np)

            body = '\n'.join(body_parts)

            # 물품설명 / 결정사유 분리
            desc_m   = re.search(r'1\.\s*물품설명(.+?)(?=2\.\s*결정사유|\Z)', body, re.DOTALL)
            reason_m = re.search(r'2\.\s*결정사유(.+?)(?===\s*PAGE|\Z)',       body, re.DOTALL)
            description = desc_m.group(1).strip()   if desc_m   else body[:800].strip()
            reason      = reason_m.group(1).strip() if reason_m else ""

            entries.append({
                "entry_num":    entry_num,
                "product_ko":   product_ko,
                "product_en":   product_en,
                "hs_code":      hs_code,
                "hs_raw":       hs_raw,
                "chapter_num":  chapter_num,
                "chapter_name": chapter_name,
                "enacted":      enacted,
                "description":  description[:1500],
                "reason":       reason[:1000],
            })

    return entries


def write_txt(e: dict, idx: int) -> Path:
    code     = e['hs_code'] or "UNKNOWN"
    suffix   = f"_{idx:03d}"
    name_part = safe_fname(e['product_ko'])
    fname    = f"hs_std_{code}{suffix}_{name_part}.txt"
    path     = OUT_DIR / fname
    section  = e['hs_code'][:2] if e['hs_code'] else ""

    header = (
        f"---\n"
        f"hs_code: {e['hs_code']}\n"
        f"source: HS_Code_standard_지침_{e['chapter_num']}장\n"
        f"pub_year: {PUB_YEAR}\n"
        f"section: {section}류\n"
        f"chapter: 제{e['chapter_num']}장 {e['chapter_name']}\n"
        f"enacted: {e['enacted']}\n"
        f"---\n"
    )
    body_lines = [
        f"【품목명】 {e['product_ko']}",
        f"【영문명】 {e['product_en']}",
        f"【HS Code】 {e['hs_raw']} (HSK2022: {e['hs_code']})",
        f"【제조공정】 제{e['chapter_num']}장 {e['chapter_name']}",
    ]
    if e['description']:
        body_lines += ["", "【물품설명】", e['description']]
    if e['reason']:
        body_lines += ["", "【결정사유】", e['reason']]

    path.write_text(header + '\n'.join(body_lines), encoding="utf-8")
    return path


def main():
    print(f"[1/4] 읽기: {SRC.name}  ({SRC.stat().st_size:,} bytes)")
    text = SRC.read_text(encoding="utf-8")

    print("[2/4] 파싱 중...")
    entries = parse(text)
    with_hs  = [e for e in entries if e['hs_code']]
    no_hs    = [e for e in entries if not e['hs_code']]
    print(f"      → 전체 {len(entries)}개  |  HS코드 확인 {len(with_hs)}개  |  누락 {len(no_hs)}개")

    print(f"[3/4] TXT 생성 → {OUT_DIR}")
    saved = []
    for idx, e in enumerate(with_hs, 1):
        p = write_txt(e, idx)
        saved.append(p)
    print(f"      → {len(saved)}개 파일 저장 완료")

    print("[4/4] 샘플 확인 (처음 5개):")
    for e in with_hs[:5]:
        print(f"      [{e['chapter_num']}장] {e['product_ko'][:28]:<28} → {e['hs_raw']}")

    dist = Counter(e['hs_code'][:4] for e in with_hs)
    print("\n[HS 호(4자리) 분포 Top-10]")
    for code, cnt in dist.most_common(10):
        print(f"  {code}호: {cnt}개")

    print(f"\n[완료]  {len(saved)}개 파일 → Pinecone 적재 준비 완료")
    return len(saved)


if __name__ == "__main__":
    main()
