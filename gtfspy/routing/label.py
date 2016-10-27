
class _LabelBase(object):

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        else:
            return False

    def __ne__(self, other):
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        else:
            return False

    def __hash__(self):
        """Override the default hash behavior (that returns the id or the object)"""
        return hash(tuple(sorted(self.__dict__.items())))


class LabelTime(_LabelBase):
    """
    LabelTime describes entries in a Profile.
    """
    def __init__(self, departure_time=-float("inf"), arrival_time_target=float('inf')):
        self.departure_time = departure_time
        self.arrival_time_target = arrival_time_target

    def dominates(self, other):
        return self.departure_time >= other.departure_time and self.arrival_time_target <= other.arrival_time_target

    def get_copy(self):
        return LabelTime(self.departure_time, self.arrival_time_target)

    def get_copy_with_specified_departure_time(self, departure_time):
        return LabelTime(departure_time, self.arrival_time_target)

    @staticmethod
    def direct_walk_label(departure_time, walk_duration):
        return LabelTime(departure_time, departure_time + walk_duration)

    def duration(self):
        return self.arrival_time_target - self.departure_time


class LabelTimeAndVehLegCount(_LabelBase):

    def __init__(self, departure_time=None, arrival_time_target=None, n_vehicle_legs=0):
        self.departure_time = departure_time
        self.arrival_time_target = arrival_time_target
        self.n_vehicle_legs = n_vehicle_legs

    def dominates(self, other):
        """
        Compute whether this LabelWithNumberVehicles dominates the other LabelWithNumberVehicles

        Parameters
        ----------
        other: LabelTimeAndVehLegCount

        Returns
        -------
        dominates: bool
            True if this ParetoTuple dominates the other, otherwise False
        """
        dominates = (
            self.departure_time >= other.departure_time and
            self.arrival_time_target <= other.arrival_time_target and
            self.n_vehicle_legs <= other.n_vehicle_legs
        )
        return dominates

    def get_copy(self):
        return LabelTimeAndVehLegCount(self.departure_time, self.arrival_time_target, self.n_vehicle_legs)

    def get_copy_with_specified_departure_time(self, departure_time):
        return LabelTimeAndVehLegCount(departure_time, self.arrival_time_target, self.n_vehicle_legs)

    @staticmethod
    def direct_walk_label(departure_time, walk_duration):
        return LabelTimeAndVehLegCount(departure_time, departure_time + walk_duration, 0)


class LabelVehLegCount(_LabelBase):

    def __init__(self, departure_time, n_vehicle_legs=0, **kwargs):
        self.departure_time = departure_time
        self.n_vehicle_legs = n_vehicle_legs

    def dominates(self, other):
        """
        Compute whether this LabelWithNumberVehicles dominates the other LabelWithNumberVehicles

        Parameters
        ----------
        other: LabelTimeAndVehLegCount

        Returns
        -------
        dominates: bool
            True if this ParetoTuple dominates the other, otherwise False
        """
        return self.n_vehicle_legs <= other.n_vehicle_legs

    def get_copy(self):
        return LabelVehLegCount(self.departure_time, self.n_vehicle_legs)

    def get_copy_with_specified_departure_time(self, departure_time):
        return LabelVehLegCount(departure_time, self.n_vehicle_legs)

    @staticmethod
    def direct_walk_label(departure_time, walk_duration):
        return LabelVehLegCount(departure_time, 0)


def compute_pareto_front(label_list):
    """
    Computes the Pareto frontier of a given label_list

    Parameters
    ----------
    label_list: list[LabelTime]
        (Or any list of objects, for which a function label.dominates(other) is defined.

    Returns
    -------
    pareto_front: list[LabelTime]
        List of labels that belong to the Pareto front.

    Notes
    -----
    Code adapted from:
    http://stackoverflow.com/questions/32791911/fast-calculation-of-pareto-front-in-python
    """
    if isinstance(label_list, set):
        label_list = list(label_list)
    dominated = []
    pareto_front = []
    remaining = label_list
    while remaining:  # (is not empty)
        candidate = remaining[0]
        new_remaining = []
        is_dominated = False
        for other in remaining[1:]:
            if candidate.dominates(other):
                dominated.append(other)
            else:
                new_remaining.append(other)
                if other.dominates(candidate):
                    is_dominated = True
        if is_dominated:
            dominated.append(candidate)
        else:
            pareto_front.append(candidate)
        remaining = new_remaining
        # after each round:
        #   remaining contains Labels that are not dominated by any in the pareto_front
        #   dominated contains Labels that are dominated by some other LabelTime
        #
    return pareto_front

def merge_pareto_frontiers(labels, labels_other):
    """
    Merge two pareto frontiers by removing dominated entries.

    Parameters
    ----------
    labels: set[LabelTime]
    labels_other: set[LabelTime]

    Returns
    -------
    pareto_front_merged: set[LabelTime]
    """
    @profile
    def _get_non_dominated_entries(candidates, possible_dominators, survivor_set=None):
        if survivor_set is None:
            survivor_set = set()
        for candidate in candidates:
            candidate_is_dominated = False
            for dominator in possible_dominators:
                if dominator.dominates(candidate):
                    candidate_is_dominated = True
                    break
            if not candidate_is_dominated:
                survivor_set.add(candidate)
        return survivor_set

    survived = _get_non_dominated_entries(labels, labels_other)
    survived = _get_non_dominated_entries(labels_other, survived, survivor_set=survived)
    return survived


def min_arrival_time_target(label_set):
    if len(label_set) > 0:
        return min(label_set, key=lambda label: label.arrival_time_target).arrival_time_target
    else:
        return float('inf')


def min_n_vehicle_trips(label_set):
    if len(label_set) > 0:
        return min(label_set, key=lambda label: label.n_vehicle_trips).n_vehicle_trips
    else:
        return None
