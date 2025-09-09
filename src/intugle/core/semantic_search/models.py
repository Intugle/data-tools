from enum import StrEnum


class RelevancyCategory(StrEnum):
    MOST_RELEVANT = "most-relevant"
    RELEVANT = "relevant"
    LESS_RELEVANT = "less-relevant"
    NON_RELEVANT = "non-relevant"

    def __repr__(
        self,
    ) -> str:
        return self.value


class ScoreStrategy(StrEnum):
    MAX = "maximum"
    AVG = "weighted-avg"

    def __repr__(
        self,
    ) -> str:
        return self.value