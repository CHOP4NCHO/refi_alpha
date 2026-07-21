from abc import ABC, abstractmethod

from ..evaluator_agent.req_fidelity_review import ReqFidelityReview


class ReviewFormatter(ABC):
    @abstractmethod
    def format(self, review: ReqFidelityReview) -> str:
        pass

    @property
    @abstractmethod
    def file_extension(self) -> str:
        pass
