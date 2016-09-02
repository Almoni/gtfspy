import sys

import networkx

# the following is required when using this module as a script
# (i.e. using the if __name__ == "__main__": part at the end of this file)
from gtfs import GTFS

if __name__ == '__main__' and __package__ is None:
    # import gtfspy
    __package__ = 'gtfspy'

class NetworkExtractor(object):

    def __init__(self, gtfs):
        """
        Parameters
        ----------
        gtfs: GTFS
            the GTFS object used for fetching timetable data

        See the specifications from

        """
        self._gtfs = gtfs  # type GTFS

    def stop_to_stop_network(self):
        """
        Extract a stop-to-stop network from the

        Returns
        -------
        networkx.DiGraph

        """
        graph = networkx.DiGraph()
        stops = self._gtfs.get_stop_info()
        for stop in stops.itertuples():
            attr_dict = {
                "lat": stop.lat,
                "lon": stop.lon,
                "name": stop.name
            }
            graph.add_node(stop.stop_I, attr_dict=attr_dict)
        # get all
        segments
        for segment in segments:
            # get all stop times between the segments, and compute the mean travel time
            # get the distance
            # for each segement, get the total travel time
            # for each seg
        return graph

    def get_walk_network(self):
        """
        Get the walk network.

        Returns
        -------
        networkx.DiGraph
        """




    def extract_multi_layer_network(self):
        """
        Stop-to-stop networks + layers reflecting modality
            Ask Mikko for more details?
            Separate networks for each mode.
            Modes:
            Walking + GTFS
        """
        pass

    def extract_multilayer_temporal_network(self):
        pass

    def line_to_line_network(self):
        pass



def main():
    cmd = sys.argv[1]
    args = sys.argv[2:]
    if cmd == "directed":
        extractor = NetworkExtractor(args[0])
    elif cmd == "multilayer":
        extractor = NetworkExtractor(args[0])
    elif cmd == "temporal":
        extractor = NetworkExtractor(args[0])
    elif cmd == "temporal":
        extractor = NetworkExtractor(args[0])

if __name__ == "__main__":
    main()

