from __future__ import annotations

from playlist_downloader.models.playlist import Track
from playlist_downloader.models.search_candidate import SearchCandidate
from playlist_downloader.models.scored_candidate import ScoredCandidate
from playlist_downloader.utils.text_utils import normalize_text
from playlist_downloader.utils.time_utils import parse_duration_seconds

NEGATIVE_TERMS = {
    "analysis",
    "analise",
    "cover",
    "karaoke",
    "instrumental",
    "live",
    "lyrics",
    "reaction",
    "review",
    "remix",
    "slowed",
    "reverb",
    "tribute",
}

OFFICIAL_TERMS = {
    "official",
    "official audio",
    "official video",
    "provided to youtube",
    "topic",
}

def score_candidate(track: Track, candidate: SearchCandidate, prefer_official: bool) -> ScoredCandidate:
    reasons: list[str] = []
    score = 0

    title_query = normalize_text(track.nome)
    candidate_title = normalize_text(candidate.title)
    artist_query = normalize_text(track.primeiro_artista)
    album_query = normalize_text(track.album)
    channel_text = normalize_text(" ".join(part for part in [candidate.channel, candidate.uploader] if part))
    artist_text = normalize_text(candidate.artist)
    album_text = normalize_text(candidate.album)
    combined_text = " ".join(part for part in [candidate_title, channel_text, artist_text, album_text] if part)

    title_tokens = [token for token in title_query.split() if token]
    token_hits = sum(1 for token in title_tokens if token in candidate_title)
    title_ratio = (token_hits / len(title_tokens)) if title_tokens else 0.0
    exact_title = bool(title_query and title_query in candidate_title)
    strong_title = exact_title or title_ratio >= 0.8
    title_match = exact_title or title_ratio >= 0.6

    if exact_title:
        score += 55
        reasons.append("exact title match")
    elif strong_title:
        score += 35
        reasons.append("strong title overlap")
    elif title_match:
        score += 15
        reasons.append("partial title overlap")
    else:
        score -= 60
        reasons.append("title mismatch")

    if artist_query and artist_query in combined_text:
        score += 20
        reasons.append("artist match")

    if album_query and album_query != normalize_text("Desconhecido"):
        if album_query in combined_text:
            score += 10
            reasons.append("album match")

    if candidate.duration is not None:
        requested_duration = parse_duration_seconds(track.duracao)
        if requested_duration is not None:
            delta = abs(candidate.duration - requested_duration)
            if delta <= 5:
                score += 10
                reasons.append("duration close")
            elif delta <= 15:
                score += 5
                reasons.append("duration plausible")
            elif delta >= 45:
                score -= 15
                reasons.append("duration mismatch")

    negative_hits = [term for term in NEGATIVE_TERMS if term in combined_text]
    if negative_hits:
        score -= 20 * len(negative_hits)
        reasons.append(f"negative terms: {', '.join(sorted(negative_hits))}")

    official_hits = [term for term in OFFICIAL_TERMS if term in combined_text]
    if prefer_official and official_hits:
        score += 15
        reasons.append("official signal")

    return ScoredCandidate(
        candidate=candidate,
        score=score,
        reasons=reasons,
        title_match=title_match,
    )


def choose_best_candidate(
    track: Track,
    candidates: list[SearchCandidate],
    prefer_official: bool,
    minimum_score: int = 40,
) -> ScoredCandidate | None:
    scored_candidates = rank_candidates(track, candidates, prefer_official)
    if not scored_candidates:
        return None
    best_candidate = scored_candidates[0]
    if not best_candidate.title_match or best_candidate.score < minimum_score:
        return None
    return best_candidate


def rank_candidates(
    track: Track,
    candidates: list[SearchCandidate],
    prefer_official: bool,
) -> list[ScoredCandidate]:
    ranked = [score_candidate(track, candidate, prefer_official) for candidate in candidates]
    ranked.sort(key=lambda item: item.score, reverse=True)
    return ranked
