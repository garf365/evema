import logging
from enum import Enum

from pulp import (
    PULP_CBC_CMD,
    LpMinimize,
    LpProblem,
    LpStatus,
    LpStatusOptimal,
    LpVariable,
    lpSum,
    value,
)

logger = logging.getLogger(__name__)


class FriendMode(Enum):
    STRICT = 1
    AT_BEST = 2
    NONE = 3


class Scheduler:
    def __init__(self, event, base=None):
        self.event = event
        self.base = base
        self.slots = event.schedule_slots()

        self.unduplicated_roles = {
            role: [slot for slot in self.slots if slot.is_contained_by(role.slot)]
            for role in event.role_set.all()
        }
        self.roles = {
            (role, idx): slots
            for role, slots in self.unduplicated_roles.items()
            for idx in range(0, role.occurence)
        }
        logger.debug(self.roles)

        self.volunteers = event.volunteeravailability_set.prefetch_related(
            "friend", "volunteerslot_set"
        ).all()

        self.fixed_slots = []
        if base is not None:
            self.fixed_slots = (
                self.base.eventscheduleslot_set.filter(volunteer__isnull=False)
                .prefetch_related("volunteer", "role")
                .all()
            )

        self.problem = None
        self._friend_mode = FriendMode.STRICT

        self.friendship = {}
        friend_done = set()
        for v in self.volunteers:
            if v in friend_done:
                continue
            if v.friend and v.friend.friend and v.friend.friend == v:
                logger.debug(f"Set {v} and {v.friend} as friends")
                common_availabilities = set(v.slots).intersection(set(v.friend.slots))
                common_slots = [
                    slot
                    for slot in self.slots
                    if any(
                        slot.is_contained_by(availability)
                        for availability in common_availabilities
                    )
                ]
                logger.debug(f"Friendship common slots: {common_slots}")

                friend_done.add(v)
                friend_done.add(v.friend)
                self.friendship[(v, v.friend)] = common_slots

    @property
    def friend_mode(self):
        return self._friend_mode

    @friend_mode.setter
    def friend_mode(self, mode):
        if mode != self._friend_mode:
            self.problem = None
            self._friend_mode = mode

    @property
    def is_valid(self):
        if self.problem is None:
            self._schedule()
        return self.problem is not None and self.problem.status == LpStatusOptimal

    @property
    def schedule(self):
        if not self.is_valid:
            return {}
        return self._scheduled

    @property
    def missing(self):
        if not self.is_valid:
            return []
        return self._missing

    # TODO simplify, too complex
    def _schedule(self):
        self.problem = LpProblem("event", LpMinimize)

        choices = LpVariable.dicts(
            "Choice", (self.volunteers, self.roles.keys(), self.slots), cat="Binary"
        )
        places_not_used = LpVariable.dicts(
            "PlacesNotUsed", (self.volunteers, self.roles.keys()), cat="Binary"
        )
        places = LpVariable.dicts(
            "Places", (self.volunteers, self.roles.keys()), cat="Binary"
        )
        friendship = LpVariable.dicts(
            "Friendship",
            (self.friendship.keys(), self.unduplicated_roles, self.slots),
            cat="Binary",
        )
        friendshipMin = LpVariable.dicts(
            "FriendshipMin",
            (self.friendship.keys(), self.unduplicated_roles, self.slots),
            cat="Float",
        )
        friendshipMax = LpVariable.dicts(
            "FriendshipMax",
            (self.friendship.keys(), self.unduplicated_roles, self.slots),
            cat="Float",
        )

        # only one person by time slot
        self._missing = {r: [] for r in self.roles.keys()}
        for r, needs in self.roles.items():
            for s in self.slots:
                if s in needs:
                    logger.debug(f"Set {r} at {s} as needed")
                    self.problem += (
                        lpSum([choices[v][r][s] for v in self.volunteers]) <= 1
                    )
                    self._missing[r].append(s)
                else:
                    logger.debug(f"Set {r} at {s} as unneeded")
                    self.problem += (
                        lpSum([choices[v][r][s] for v in self.volunteers]) == 0
                    )

        # only one post by time slot and person
        for v in self.volunteers:
            for s in self.slots:
                self.problem += (
                    lpSum([choices[v][r][s] for r in self.roles.keys()]) <= 1
                )
            for r in self.roles.keys():
                self.problem += places_not_used[v][r] <= 1 - 1 / (
                    len(self.slots) + 1
                ) * lpSum([choices[v][r][s] for s in self.slots])
                self.problem += places_not_used[v][r] >= 0.5 - lpSum(
                    [choices[v][r][s] for s in self.slots]
                )
                self.problem += places[v][r] == 1 - places_not_used[v][r]

        # regroup friends
        if self._friend_mode != FriendMode.NONE:
            for v, common_slots in self.friendship.items():
                if self._friend_mode == FriendMode.STRICT:
                    for r, s in [
                        (r, s)
                        for r in self.unduplicated_roles
                        for s in self.slots
                        if s in common_slots
                    ]:
                        if r.occurence >= 2:
                            logger.debug(
                                f"Set {v[0]} and {v[1]} as possible on {r} for {s}"
                            )
                            self.problem += (
                                choices[v[0]][(r, 0)][s] == choices[v[1]][(r, 1)][s]
                            )
                        else:
                            self.problem += choices[v[0]][(r, 0)][s] == 0
                            self.problem += choices[v[1]][(r, 0)][s] == 0
                elif self._friend_mode == FriendMode.AT_BEST:
                    for r, n, s in [
                        (r, n, s)
                        for r, n in self.unduplicated_roles.items()
                        for s in self.slots
                    ]:
                        if r.occurence >= 2 and s in common_slots and s in n:
                            logger.debug(
                                f"Set {v[0]} and {v[1]} as possible on {r} for {s}"
                            )
                            self.problem += friendshipMax[v][r][s] == (
                                1 / len(v)
                            ) * lpSum(
                                [
                                    choices[f][(r, p)][s]
                                    for f in v
                                    for p in range(0, r.occurence)
                                ]
                            )
                            self.problem += friendshipMin[v][r][s] == (
                                1 / len(v)
                            ) * lpSum(
                                [
                                    choices[f][(r, p)][s]
                                    for f in v
                                    for p in range(0, r.occurence)
                                ]
                            ) - (
                                (len(v) - 1) / len(v)
                            )
                            self.problem += (
                                friendship[v][r][s] <= friendshipMax[v][r][s]
                            )
                            self.problem += (
                                friendship[v][r][s] >= friendshipMin[v][r][s]
                            )
                        else:
                            self.problem += friendship[v][r][s] == 0
                            self.problem += (
                                friendship[v][r][s] == friendshipMax[v][r][s]
                            )
                            self.problem += (
                                friendship[v][r][s] == friendshipMin[v][r][s]
                            )

        # be sure availability of people
        for v in self.volunteers:
            for s in self.slots:
                if not any(s.is_contained_by(availability) for availability in v.slots):
                    logger.debug(f"Set {v} as unavailable at {s}")
                    for r in self.roles.keys():
                        self.problem += choices[v][r][s] == 0
            # not on role with incorrect category
            if v.categories.exists():
                for r in self.roles.keys():
                    if r[0].category and r[0].category not in v.categories.all():
                        logger.debug(f"Set {v} as unavailable for {r}")
                        for s in self.slots:
                            self.problem += choices[v][r][s] == 0

        # force place
        for fixed in self.fixed_slots:
            self.problem += (
                choices[fixed.volunteer][(fixed.role, fixed.position)][fixed.slot] == 1
            )

        # Count how many slots are filled
        self.problem += lpSum(
            [
                -choices[v][r][s] * r[0].weight
                for v in self.volunteers
                for r in self.roles.keys()
                for s in self.slots
            ]
            + [places[v][r] for v in self.volunteers for r in self.roles.keys()]
            + [
                -3 * friendship[f][r][s]
                for f in self.friendship.keys()
                for r in self.unduplicated_roles
                for s in self.slots
            ]
        )

        self.problem.solve(PULP_CBC_CMD(timeLimit=120))

        logger.debug(f"Status:{LpStatus[self.problem.status]}")

        if self.problem.status != LpStatusOptimal:
            return

        self._scheduled = {}
        for v in self.volunteers:
            self._scheduled[v] = {}
            for s in self.slots:
                self._scheduled[v][s] = []
                for r in self.roles:
                    if value(choices[v][r][s]) == 1:
                        logger.debug(
                            f"{v.volunteer.firstname} => "
                            f"{r[0].name}-{r[1]} at {s.start}"
                        )
                        self._scheduled[v][s].append(r)
                        self._missing[r].remove(s)
            for r in self.roles:
                if value(places[v][r]) == 1:
                    logger.debug(
                        f"{v.volunteer.firstname} will be at {r[0].name}-{r[1]}"
                    )

        for f in self.friendship:
            for r in self.unduplicated_roles:
                for s in self.slots:
                    logger.debug(
                        f"{f} : {value(friendshipMin[f][r][s])} <= "
                        f"{value(friendship[f][r][s])} <= "
                        f"{value(friendshipMax[f][r][s])} => "
                        f"{r.name} at {s.start}"
                    )

        # remove empty slots
        self._scheduled = {
            v: {s: r[0] for s, r in scheduled.items() if r}
            for v, scheduled in self._scheduled.items()
        }
