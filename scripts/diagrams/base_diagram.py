from abc import ABC, abstractmethod

class BaseDiagram(ABC):
    """Abstract base class for all diagram generators."""
    def __init__(self, context_data, title, settings):
        self.context_data = context_data
        self.title = title
        self.settings = settings
        self.template = self.settings.get("visualizations", {}).get("plotly_template", "plotly_white")

    @abstractmethod
    def generate(self):
        """
        This method must be implemented by every diagram class.
        It should return a Plotly Figure object.
        """
        pass
