"""One decision rule for shortlist, export, explanations and audits."""

import math
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class SelectionPolicy:
    threshold: float = 0.5
    top_n: int | None = None

    def __post_init__(self):
        if (
            isinstance(self.threshold, bool)
            or not isinstance(self.threshold, (float, int))
            or not math.isfinite(self.threshold)
            or not 0 <= self.threshold <= 1
        ):
            raise ValueError("Threshold must be a finite number between 0 and 1.")
        if self.top_n is not None and (
            isinstance(self.top_n, bool)
            or not isinstance(self.top_n, int)
            or not 1 <= self.top_n <= 100000
        ):
            raise ValueError("Capacity must be an integer from 1 to 100,000, or blank.")

    def select(self, rows, probabilities):
        if len(rows) != len(probabilities):
            raise ValueError("Rows and scores must have identical lengths.")
        ranked = sorted(
            range(len(rows)),
            key=lambda i: (-float(probabilities[i]), str(rows[i]["enrollee_id"])),
        )
        if self.top_n is not None:
            chosen = set(ranked[: self.top_n])
            return [int(i in chosen) for i in range(len(rows))], ranked
        return [int(p >= self.threshold) for p in probabilities], ranked

    def to_dict(self):
        return {
            **asdict(self),
            "mode": "top_n" if self.top_n is not None else "threshold",
            "tie_rule": "Unrounded score descending, then applicant ID ascending",
            "description": f"Top {self.top_n:,} records"
            if self.top_n is not None
            else f"Score ≥ {self.threshold:.2f}",
        }

    @classmethod
    def parse(cls, data, default=None):
        default = default or cls()
        raw_n = data.get("top_n", default.top_n)
        try:
            if raw_n in ("", None):
                top_n = None
            else:
                if isinstance(raw_n, bool) or str(raw_n).strip() != str(int(raw_n)):
                    raise ValueError()
                top_n = int(raw_n)
            raw_t = data.get("threshold", default.threshold)
            if isinstance(raw_t, bool):
                raise ValueError()
            threshold = float(raw_t)
        except (TypeError, ValueError, OverflowError):
            raise ValueError(
                "Use a numeric threshold and an integer capacity."
            ) from None
        return cls(threshold, top_n)
