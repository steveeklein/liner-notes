from abc import ABC, abstractmethod
from typing import List
from app.models import InfoCard


class DataSource(ABC):
    """Base class for all data sources."""
    
    @abstractmethod
    async def fetch(
        self,
        artist: str,
        track_title: str,
        album: str,
        track_id: str,
        **kwargs
    ) -> List[InfoCard]:
        """Fetch info cards from this data source. kwargs may include variation=True for refresh (new content)."""
        pass
