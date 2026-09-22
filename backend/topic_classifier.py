import re
from typing import List, Dict, Tuple, Optional
from pydantic import BaseModel, Field

from backend.schemas import TopicCategory

class ClassificationResult(BaseModel):
    category: TopicCategory
    confidence: float = Field(ge=0.0, le=1.0)
    summary_bullets: List[str] = Field(default_factory=list)

class TopicClassifier:
    """
    Taxonomy classification and neutral resident summary generator for municipal documents.
    """

    TOPIC_KEYWORDS: Dict[TopicCategory, List[str]] = {
        TopicCategory.TAXES_BUDGET: [
            "tax", "taxes", "taxation", "millage", "levy", "assessment", "assessed valuation",
            "budget", "appropriation", "appropriations", "fiscal year", "general fund",
            "bond proceeds", "debt service", "revenue", "expenditure", "audit", "fee schedule"
        ],
        TopicCategory.ZONING_LAND_USE: [
            "zoning", "rezoning", "variance", "setback", "rear yard", "front yard", "side yard",
            "land use", "subdivision", "special use permit", "conditional use", "comprehensive plan",
            "parcel", "lot", "easement", "plat", "building height", "density", "residential district",
            "commercial district", "mixed-use", "stormwater retention", "site plan"
        ],
        TopicCategory.EDUCATION_SCHOOLS: [
            "school", "schools", "school board", "superintendent", "education", "classroom",
            "elementary", "middle school", "high school", "stem", "curriculum", "student",
            "teacher", "academic", "enrollment", "athletic department"
        ],
        TopicCategory.PUBLIC_SAFETY: [
            "police", "fire", "fire rescue", "sheriff", "emergency", "911", "dispatch",
            "patrol", "ambulance", "tactical", "radio repeater", "communications upgrade",
            "public safety", "hazard", "code enforcement", "first responder"
        ],
        TopicCategory.PARKS_REC_ENVIRONMENT: [
            "park", "parks", "recreation", "greenway", "trail", "riverwalk", "tree canopy",
            "open space", "playground", "athletic field", "conservation", "wildlife",
            "urban canopy", "environmental sustainability", "beautification"
        ],
        TopicCategory.GENERAL_ADMIN: [
            "proclamation", "ceremonial", "minutes", "appointment", "board commission",
            "charter", "election", "bylaws", "foia", "public notice", "adjournment"
        ]
    }

    LEGAL_BOILERPLATE_PATTERNS = [
        re.compile(r"^\s*WHEREAS\b[^\.;:]*[\.;:]\s*", re.IGNORECASE),
        re.compile(r"^\s*NOW,?\s+THEREFORE,?\s+(?:BE IT ORDAINED|BE IT RESOLVED)[^\.;:]*by[^\.;:]*that\s*", re.IGNORECASE),
        re.compile(r"^\s*BE IT (?:FURTHER )?(?:ORDAINED|RESOLVED)[^\.;:]*that\s*", re.IGNORECASE),
        re.compile(r"^\s*SECTION\s+\d+[\.\:]\s*", re.IGNORECASE),
    ]

    def classify(self, text: str) -> Tuple[TopicCategory, float]:
        text_lower = text.lower()
        scores: Dict[TopicCategory, float] = {cat: 0.0 for cat in TopicCategory}

        for cat, keywords in self.TOPIC_KEYWORDS.items():
            for kw in keywords:
                # Count exact word or phrase occurrences
                pattern = r"\b" + re.escape(kw) + r"\b"
                matches = len(re.findall(pattern, text_lower))
                if matches > 0:
                    # Weight multi-word matches more heavily
                    weight = 1.5 if " " in kw else 1.0
                    scores[cat] += matches * weight

        best_cat = max(scores, key=lambda c: scores[c])
        total_score = sum(scores.values())

        if total_score == 0:
            return TopicCategory.GENERAL_ADMIN, 0.5

        raw_confidence = scores[best_cat] / total_score
        confidence = min(1.0, max(0.65, 0.5 + (raw_confidence * 0.5)))
        return best_cat, round(confidence, 2)

    def extract_neutral_bullets(self, text: str, max_bullets: int = 3) -> List[str]:
        cleaned_lines = []
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            # Strip boilerplate
            for bp in self.LEGAL_BOILERPLATE_PATTERNS:
                line = bp.sub("", line).strip()

            if line and len(line) > 15:
                cleaned_lines.append(line)

        combined_cleaned = " ".join(cleaned_lines)
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', combined_cleaned) if len(s.strip()) > 15]

        # If standard punctuation split produced no sentences, fall back to cleaned lines
        if not sentences and cleaned_lines:
            sentences = [re.sub(r'^(?:[-*•]|\d+[\.\)])\s*', '', cl).strip() for cl in cleaned_lines if len(cl.strip()) > 15]

        # Prioritize key action-oriented sentences
        action_keywords = ["approv", "authoriz", "allocat", "adopt", "setback", "variance", "rate", "$", "parcel", "street", "permit", "grant", "purchas", "resolv", "ordin"]
        scored_sentences = []
        for s in sentences:
            s_clean = re.sub(r'^(?:[-*•]|\d+[\.\)])\s*', '', s).strip()
            if not s_clean or len(s_clean) < 15:
                continue
            # Skip lingering whereas/hereby preamble fragments
            if s_clean.upper().startswith("WHEREAS") or s_clean.upper().startswith("NOW, THEREFORE") or s_clean.upper().startswith("BE IT ORDAINED"):
                continue
            
            score = sum(1 for kw in action_keywords if kw in s_clean.lower())
            scored_sentences.append((score, s_clean))

        scored_sentences.sort(key=lambda x: x[0], reverse=True)

        selected_bullets = []
        for score, sent in scored_sentences:
            if sent not in selected_bullets:
                selected_bullets.append(sent)
            if len(selected_bullets) >= max_bullets:
                break

        if not selected_bullets and sentences:
            selected_bullets = [re.sub(r'^(?:[-*•]|\d+[\.\)])\s*', '', s).strip() for s in sentences[:max_bullets]]

        return selected_bullets

    def classify_and_summarize(self, text: str) -> ClassificationResult:
        category, confidence = self.classify(text)
        bullets = self.extract_neutral_bullets(text)
        return ClassificationResult(
            category=category,
            confidence=confidence,
            summary_bullets=bullets
        )
