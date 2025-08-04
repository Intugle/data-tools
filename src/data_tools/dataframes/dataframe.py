from abc import ABC, abstractmethod


class DataFrame(ABC):

    @abstractmethod
    def profile(self):
        pass
