from abc import ABCMeta, abstractmethod

import copy

from gtfspy.routing.models import ParetoTuple


class AbstractNodeProfile:
    """ Defines the NodeProfile interface """

    __metaclass__ = ABCMeta

    def __init__(self):
        pass

    @abstractmethod
    def update_pareto_optimal_tuples(self, new_pareto_tuple):
        pass

    @abstractmethod
    def get_earliest_arrival_time_at_target(self, dep_time):
        pass

    @abstractmethod
    def get_pareto_tuples(self):
        pass


class NodeProfile(AbstractNodeProfile):
    """
    In the connection scan algorithm, each stop has a profile entry
    that stores information on the Pareto-Optimal
    (departure_time_this_node, arrival_time_target_node) tuples.
    """

    def __init__(self):
        super(NodeProfile, self).__init__()
        self._pareto_tuples = set()  # set[ParetoTuple]

    def update_pareto_optimal_tuples(self, new_pareto_tuple):
        """
        # this function should be optimized

        Parameters
        ----------
        new_pareto_tuple: ParetoTuple

        Returns
        -------
        added: bool
            whether pareto_tuple was
        """
        new_is_dominated_by_old_tuples = False

        old_tuples_dominated_by_new = set()
        for old_pareto_tuple in self._pareto_tuples:
            if old_pareto_tuple.dominates(new_pareto_tuple):
                new_is_dominated_by_old_tuples = True
                break
            if new_pareto_tuple.dominates(old_pareto_tuple):
                old_tuples_dominated_by_new.add(old_pareto_tuple)
        if new_is_dominated_by_old_tuples:
            assert (len(old_tuples_dominated_by_new) == 0)
            return False
        else:
            self._pareto_tuples.difference_update(old_tuples_dominated_by_new)
            self._pareto_tuples.add(new_pareto_tuple)
            return True

    def get_earliest_arrival_time_at_target(self, dep_time):
        """
        Get the earliest arrival time at the target, given a departure time.

        Parameters
        ----------
        dep_time : float, int
            time in unix seconds

        Returns
        -------
        arrival_time : float
            Arrival time in the given time unit (seconds after unix epoch).
        """
        minimum = float('inf')
        for pt in self._pareto_tuples:
            if pt.departure_time > dep_time and pt.arrival_time_target < minimum:
                minimum = pt.arrival_time_target
        return float(minimum)

    def get_pareto_tuples(self):
        return copy.deepcopy(self._pareto_tuples)


# class DecreasingDepTimeNodeProfile(AbstractNodeProfile):
#     """
#     In the connection scan algorithm, each stop has a profile entry
#     that stores information on the Pareto-Optimal
#     (departure_time_this_node, arrival_time_target_node) tuples.
#     """
#
#     def __init__(self):
#         super(DecreasingDepTimeNodeProfile, self).__init__()
#         self._pareto_tuples = []  # set[ParetoTuple]
#
#     def update_pareto_optimal_tuples(self, new_pareto_tuple):
#         """
#         Parameters
#         ----------
#         new_pareto_tuple: ParetoTuple
#
#         Returns
#         -------
#         added: bool
#             whether the new pareto_tuple was included
#         """
#         assert(isinstance(new_pareto_tuple, ParetoTuple))
#         if len(self._pareto_tuples) > 0:
#             assert (self._pareto_tuples[-1].departure_time >= new_pareto_tuple.departure_time)
#
#         if len(self._pareto_tuples) > 0 and self._pareto_tuples[-1].dominates(new_pareto_tuple):
#             return False
#         else:
#             self._pareto_tuples.append(new_pareto_tuple)
#             return True
#
#     def get_earliest_arrival_time_at_target(self, dep_time):
#         minimum = float('inf')
#         for pt in self._pareto_tuples:
#             if pt.departure_time > dep_time and pt.arrival_time_target < minimum:
#                 minimum = pt.arrival_time_target
#         return minimum
#
#     def get_pareto_tuples(self):
#         return self._pareto_tuples


class IdentityNodeProfile(AbstractNodeProfile):

    def __init__(self):
        super(IdentityNodeProfile, self).__init__()

    def update_pareto_optimal_tuples(self, new_pareto_tuple):
        return False

    def get_earliest_arrival_time_at_target(self, dep_time):
        return dep_time

    def get_pareto_tuples(self):
        return []
