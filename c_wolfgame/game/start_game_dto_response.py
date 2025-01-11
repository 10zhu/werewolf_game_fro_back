from dataclasses import dataclass, asdict

@dataclass
class StartGameResponseDto:
    type: str
    phase: str

    def to_json(self):
        return asdict(self)
