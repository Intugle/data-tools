from enum import Enum


class RelevancyCategory(str, Enum):
    MOST_RELEVANT = "most-relevant"
    RELEVANT = "relevant"
    LESS_RELEVANT = "less-relevant"
    NON_RELEVANT = "non-relevant"

    def __repr__(
        self,
    ) -> str:
        return self.value


class ScoreStrategy(str, Enum):
    MAX = "maximum"
    AVG = "weighted-avg"

    def __repr__(
        self,
    ) -> str:
        return self.value