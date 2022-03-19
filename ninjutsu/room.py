from enum import Enum


class RoomStatus(Enum):
    PROGRESS = 1
    RESULT = 2


class Counter:
    def __init__(self):
        self.c = 0

    def next(self):
        self.c += 1
        return self.c


class Room:
    def __init__(self, id):
        self._id = id
        self._counter = Counter()
        self._votes = {}
        self.status = RoomStatus.PROGRESS
        self._subscribers = []

    def subscribe(self, subscriber):
        self._subscribers.append(subscriber)

    def unsubscribe(self, subscriber):
        self._subscribers.remove(subscriber)

    def new_player(self):
        player = Player(id=self._counter.next())
        self._votes[player] = None
        self._publish("new_player", player=player)
        return player

    def remove_player(self, player):
        del self._votes[player]
        self._publish("remove_player", player=player)

    def vote(self, player, vote):
        self._votes[player] = vote
        self._publish("vote_placed", player=player, vote=vote)

    def get_players(self):
        return self._votes.keys()

    def get_votes(self):
        return self._votes.items()

    def _publish(self, event, **kwargs):
        for subscriber in self._subscribers:
            subscriber(self, event, **kwargs)


class Player:
    def __init__(self, id):
        self.id = id
