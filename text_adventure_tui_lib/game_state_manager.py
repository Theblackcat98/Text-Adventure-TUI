from .data_structures import GameState, Player, Story
from typing import Dict, Any, List

class GameStateManager:
    def __init__(self, game_state: GameState):
        self.game_state = game_state

    def get_player(self) -> Player:
        return self.game_state.player

    def get_story(self) -> Story:
        return self.game_state.current_story

    def get_flags(self) -> Dict[str, bool]:
        return self.game_state.flags

    def set_flag(self, flag: str):
        self.game_state.flags[flag] = True

    def clear_flag(self, flag: str):
        if flag in self.game_state.flags:
            del self.game_state.flags[flag]

    def get_inventory(self) -> List[str]:
        return self.game_state.player.inventory

    def add_item(self, item: str):
        if item not in self.game_state.player.inventory:
            self.game_state.player.inventory.append(item)

    def remove_item(self, item: str):
        if item in self.game_state.player.inventory:
            self.game_state.player.inventory.remove(item)

    def get_stats(self) -> Dict[str, Any]:
        return self.game_state.player.stats

    def update_stat(self, stat: str, value: Any):
        self.game_state.player.stats[stat] = value
        
    def get_current_location(self) -> str:
        return self.game_state.current_location

    def set_current_location(self, location: str):
        if self.game_state.current_location != location:
            self.game_state.current_location = location
            self.game_state.turns_in_location = 0

    def increment_turns_in_location(self):
        self.game_state.turns_in_location += 1

    def get_turn_count(self) -> int:
        return self.game_state.turn_count

    def increment_turn(self):
        self.game_state.turn_count += 1
