from dataclasses import dataclass
from typing import Iterable, Optional

from models import Durum


@dataclass(frozen=True)
class RevisionLetterCandidate:
    logical_type: str
    broad_type: str
    yazi_no: str
    yazi_tarih: Optional[str]
    source_field: str


_TYPE_ALIASES = {
    "gelen": "gelen",
    "gelen yazi": "gelen",
    "gelen yazı": "gelen",
    "gelen_yazi": "gelen",
    "onay": "onay",
    "notlu onay": "onay",
    "notlu_onay": "onay",
    "notlu": "onay",
    "red": "red",
    "reddet": "red",
    "giden": "giden",
    "giden onay": "giden",
    "giden_onay": "giden",
    "yok": "yok",
}


def normalize_revision_letter_type(value: Optional[str]) -> Optional[str]:
    text = (value or "").strip().lower()
    if not text:
        return None
    return _TYPE_ALIASES.get(text, text)


def iter_revision_letter_candidates(rev) -> Iterable[RevisionLetterCandidate]:
    if not rev:
        return ()

    candidates = []
    gelen_no = (getattr(rev, "gelen_yazi_no", None) or "").strip()
    onay_no = (getattr(rev, "onay_yazi_no", None) or "").strip()
    red_no = (getattr(rev, "red_yazi_no", None) or "").strip()

    if gelen_no:
        candidates.append(
            RevisionLetterCandidate(
                logical_type="gelen",
                broad_type="gelen",
                yazi_no=gelen_no,
                yazi_tarih=getattr(rev, "gelen_yazi_tarih", None),
                source_field="gelen_yazi_no",
            )
        )
    if onay_no:
        candidates.append(
            RevisionLetterCandidate(
                logical_type="onay",
                broad_type="giden",
                yazi_no=onay_no,
                yazi_tarih=getattr(rev, "onay_yazi_tarih", None),
                source_field="onay_yazi_no",
            )
        )
    if red_no:
        candidates.append(
            RevisionLetterCandidate(
                logical_type="red",
                broad_type="giden",
                yazi_no=red_no,
                yazi_tarih=getattr(rev, "red_yazi_tarih", None),
                source_field="red_yazi_no",
            )
        )
    return tuple(candidates)


def has_revision_letter(rev) -> bool:
    return any(iter_revision_letter_candidates(rev))


def _status_preferred_logical_type(status: Optional[str]) -> Optional[str]:
    if status == Durum.REDDEDILDI.value:
        return "red"
    if status in {Durum.ONAYLI.value, Durum.ONAYLI_NOTLU.value}:
        return "onay"
    return None


def _candidate_score(
    candidate: RevisionLetterCandidate,
    rev,
    preferred_type: Optional[str],
    preferred_yazi_no: Optional[str],
) -> tuple[int, int]:
    score = 0
    normalized_preferred = normalize_revision_letter_type(preferred_type)
    normalized_rev_type = normalize_revision_letter_type(getattr(rev, "yazi_turu", None))
    status_preferred = _status_preferred_logical_type(getattr(rev, "durum", None))

    if preferred_yazi_no and candidate.yazi_no == preferred_yazi_no:
        score += 1000

    if normalized_preferred:
        if normalized_preferred == candidate.logical_type:
            score += 220
        elif normalized_preferred == candidate.broad_type:
            score += 170

    if status_preferred == candidate.logical_type:
        score += 130

    if normalized_rev_type:
        if normalized_rev_type == candidate.logical_type:
            score += 110
        elif normalized_rev_type == candidate.broad_type:
            score += 85

    broad_priority = 20 if candidate.broad_type == "giden" else 10
    logical_priority = {"onay": 3, "red": 2, "gelen": 1}.get(candidate.logical_type, 0)
    return score, broad_priority + logical_priority


def resolve_revision_letter_candidate(
    rev,
    *,
    preferred_type: Optional[str] = None,
    preferred_yazi_no: Optional[str] = None,
) -> Optional[RevisionLetterCandidate]:
    candidates = list(iter_revision_letter_candidates(rev))
    if not candidates:
        return None

    indexed = list(enumerate(candidates))
    indexed.sort(
        key=lambda item: (
            _candidate_score(item[1], rev, preferred_type, preferred_yazi_no),
            -item[0],
        ),
        reverse=True,
    )
    return indexed[0][1]
