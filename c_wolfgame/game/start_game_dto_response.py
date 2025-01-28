from dataclasses import dataclass, asdict, field
from typing import List, Dict


@dataclass
class StartGameResponseDto:
    type: str
    phase: str
    players: List[Dict] = field(default_factory=list)
    def to_json(self):
        return {
            'type': self.type,
            'phase': self.phase,
            'players': self.players  # Players are already in dict format
        }