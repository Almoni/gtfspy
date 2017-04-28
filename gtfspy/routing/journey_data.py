import os
import sqlite3

from gtfspy.routing.connection import Connection
from gtfspy.gtfs import GTFS
from gtfspy.routing.label import LabelTimeAndRoute, LabelTimeWithBoardingsCount, compute_pareto_front
from gtfspy.routing.node_profile_multiobjective import NodeProfileMultiObjective
from gtfspy.util import timeit


class JourneyDataManager:
    def __init__(self, gtfs_dir, routing_params, journey_db_dir=None, multitarget_routing=False, close_connection=True,
                 track_route=False, track_vehicle_legs=True):
        """

        :param gtfs: GTFS object
        :param list_of_stop_profiles: dict of NodeProfileMultiObjective
        :param multitarget_routing: bool
        """
        self.close_connection = close_connection
        self.routing_params = routing_params
        self.multitarget_routing = multitarget_routing
        self.track_route = track_route
        self.track_vehicle_legs = track_vehicle_legs
        self.gtfs_dir = gtfs_dir
        self.gtfs = GTFS(self.gtfs_dir)
        self.gtfs_meta = self.gtfs.meta
        self.gtfs._dont_close = True
        print('location_name: ', self.gtfs_meta["location_name"])
        self.conn = None
        if journey_db_dir:
            if os.path.isfile(journey_db_dir):
                self.conn = sqlite3.connect(journey_db_dir)
                self.parameters = Parameters(self.conn)
                self._check_that_dbs_match()

            else:
                raise Exception("Database specified does not exist, use run_preparations() method first")

    def __del__(self):
        self.gtfs._dont_close = False
        if self.conn:
            self.conn.close()

    @timeit
    def import_journey_data_single_stop(self, list_of_stop_profiles, target_stop):
        cur = self.conn.cursor()
        self.conn.isolation_level = 'EXCLUSIVE'
        cur.execute('PRAGMA synchronous = OFF;')
        if not isinstance(list_of_stop_profiles, list):
            list_of_stop_profiles = [list_of_stop_profiles]
        if self.track_route:
            self._insert_journeys_with_route_into_db(list_of_stop_profiles)
        else:
            self._insert_journeys_into_db_no_route(list_of_stop_profiles, target_stop=target_stop)

        if self.close_connection:
            self.conn.close()

        print("Finished import process")

    def _check_that_dbs_match(self):
        for key, value in self.parameters.items():
            if key in self.gtfs_meta.keys():
                assert self.gtfs_meta[key] == value

    def _check_last_journey_id(self):
        cur = self.conn.cursor()
        val = cur.execute("select max(journey_id) FROM journeys").fetchone()
        return val[0] if val[0] else 0

    def _insert_journeys_into_db_no_route(self, list_of_stop_profiles, target_stop=None):
        # TODO: Change the insertion so that the check last journey id and insertions are in the same transaction block
        """
        con.isolation_level = 'EXCLUSIVE'
        con.execute('BEGIN EXCLUSIVE')
        #exclusive access starts here. Nothing else can r/w the db, do your magic here.
        con.commit()
        """
        print("Collecting journey data")
        journey_id = 1
        journey_list = []
        for stop_profiles in list_of_stop_profiles:
            tot = len(stop_profiles)
            for i, origin_stop in enumerate(stop_profiles, start=1):
                #print("\r Stop " + str(i) + " of " + str(tot), end='', flush=True)

                assert (isinstance(stop_profiles[origin_stop], NodeProfileMultiObjective))

                for label in stop_profiles[origin_stop].get_final_optimal_labels():
                    assert (isinstance(label, LabelTimeWithBoardingsCount))
                    if self.multitarget_routing:
                        target_stop = None

                    values = [journey_id,
                              origin_stop,
                              target_stop,
                              int(label.departure_time),
                              int(label.arrival_time_target),
                              label.n_boardings]

                    journey_list.append(values)
                    journey_id += 1
            print("Inserting journeys into database")
            insert_journeys_stmt = '''INSERT INTO journeys(
                  journey_id,
                  from_stop_I,
                  to_stop_I,
                  dep_time,
                  arr_time,
                  n_boardings) VALUES (%s) ''' % (", ".join(["?" for x in range(6)]))
            #self.conn.executemany(insert_journeys_stmt, journey_list)

            self._execute_function(insert_journeys_stmt, journey_list)
        self.conn.commit()

    @timeit
    def _execute_function(self, statement, rows):
        self.conn.execute('BEGIN EXCLUSIVE')
        last_id = self._check_last_journey_id()
        rows = [[x[0]+last_id] + x[1:] for x in rows]
        self.conn.executemany(statement, rows)

    def _insert_journeys_with_route_into_db(self, list_of_stop_profiles):
        print("Collecting journey and connection data")
        journey_id = (self._check_last_journey_id() if self._check_last_journey_id() else 0) + 1
        journey_list = []
        connection_list = []
        for stop_profiles in list_of_stop_profiles:
            tot = len(stop_profiles)
            for i, origin_stop in enumerate(stop_profiles, start=1):
                #print("\r Stop " + str(i) + " of " + str(tot), end='', flush=True)

                assert (isinstance(stop_profiles[origin_stop], NodeProfileMultiObjective))

                for label in stop_profiles[origin_stop].get_final_optimal_labels():
                    assert (isinstance(label, LabelTimeAndRoute))
                    # We need to "unpack" the journey to actually figure out where the trip went
                    # (there can be several targets).

                    target_stop, new_connection_values, route_stops = self._collect_connection_data(journey_id, label)
                    if origin_stop == target_stop:
                        continue
                    values = [journey_id,
                              origin_stop,
                              target_stop,
                              int(label.departure_time),
                              int(label.arrival_time_target),
                              label.movement_duration,
                              route_stops]

                    journey_list.append(values)
                    connection_list += new_connection_values
                    journey_id += 1

            print()
            print("Inserting journeys into database")
            insert_journeys_stmt = '''INSERT INTO journeys(
                  journey_id,
                  from_stop_I,
                  to_stop_I,
                  dep_time,
                  arr_time,
                  movement_duration,
                  route) VALUES (%s) ''' % (", ".join(["?" for x in range(7)]))
            self.conn.executemany(insert_journeys_stmt, journey_list)

            print("Inserting connections into database")
            insert_connections_stmt = '''INSERT INTO connections(
                                  journey_id,
                                  from_stop_I,
                                  to_stop_I,
                                  dep_time,
                                  arr_time,
                                  trip_I,
                                  seq,
                                  leg_stops) VALUES (%s) ''' % (", ".join(["?" for x in range(8)]))
            self.conn.executemany(insert_connections_stmt, connection_list)
        self.conn.commit()

    def _collect_connection_data(self, journey_id, label):
        target_stop = None
        cur_label = label
        seq = 1
        value_list = []
        route_stops = []
        leg_stops = []
        prev_trip_id = None
        leg_departure_time = None
        leg_departure_stop = None
        while True:
            connection = cur_label.connection
            if isinstance(connection, Connection):
                if connection.trip_id:
                    trip_id = connection.trip_id
                else:
                    trip_id = -1

                if prev_trip_id != trip_id:
                    route_stops.append(connection.departure_stop)
                    if prev_trip_id:
                        leg_stops.append(connection.arrival_stop)
                        values = (
                            int(journey_id),
                            int(leg_departure_stop),
                            int(connection.arrival_stop),
                            int(leg_departure_time),
                            int(connection.arrival_time),
                            int(trip_id),
                            int(seq),
                            ','.join([str(x) for x in leg_stops])
                                )
                        value_list.append(values)
                        seq += 1
                        leg_stops = []
                    leg_departure_stop = connection.departure_stop
                    leg_departure_time = connection.departure_time
                leg_stops.append(connection.departure_stop)
                target_stop = connection.arrival_stop
                prev_trip_id = trip_id
            if not cur_label.previous_label:
                break
            cur_label = cur_label.previous_label
        route_stops.append(target_stop)
        route_stops = ','.join([str(x) for x in route_stops])
        return target_stop, value_list, route_stops

    @timeit
    def add_fastest_path_column(self):

        cur = self.conn.cursor()
        # Select all distinct O-D pairs
        # For O-D pair in O-D pairs, create pareto-front
        cur.execute('SELECT from_stop_I, to_stop_I FROM journeys GROUP BY from_stop_I, to_stop_I')
        od_pairs = cur.fetchall()
        # cur.execute('SELECT journey_id FROM journeys ORDER BY journey_id')
        # all_journey_ids = cur.fetchall()
        fastest_path_journey_ids = []
        for pair in od_pairs:
            cur.execute('SELECT dep_time, arr_time, journey_id FROM journeys '
                        'WHERE from_stop_I = ? AND to_stop_I = ? '
                        'ORDER BY dep_time ASC', (pair[0], pair[1]))
            all_trips = cur.fetchall()
            all_labels = [LabelTimeAndRoute(x[0], x[1], x[2], False) for x in all_trips]
            all_fp_labels = compute_pareto_front(all_labels, finalization=False, ignore_n_boardings=True)
            fastest_path_journey_ids.append(all_fp_labels)
        # all_rows = [1 if x in fastest_path_journey_ids else 0 for x in all_journey_ids]
        fastest_path_journey_ids = [(1, x.n_boardings) for sublist in fastest_path_journey_ids for x in sublist]
        cur.executemany("UPDATE journeys SET fastest_path = ? WHERE journey_id = ?", fastest_path_journey_ids)
        self.conn.commit()

    @timeit
    def add_time_to_prev_journey_fp_column(self):
        cur = self.conn.cursor()
        cur.execute('SELECT journey_id, from_stop_I, to_stop_I, dep_time FROM journeys '
                    'WHERE fastest_path = 1 '
                    'ORDER BY from_stop_I, to_stop_I, dep_time ')

        all_trips = cur.fetchall()
        time_to_prev_journey = []
        prev_dep_time = None
        prev_origin = None
        prev_destination = None
        for trip in all_trips:
            journey_id = trip[0]
            from_stop_I = trip[1]
            to_stop_I = trip[2]
            dep_time = trip[3]
            if prev_origin != from_stop_I or prev_destination != to_stop_I:
                prev_dep_time = None
            if prev_dep_time:
                time_to_prev_journey.append((dep_time - prev_dep_time, journey_id))
            prev_origin = from_stop_I
            prev_destination = to_stop_I
            prev_dep_time = dep_time
        cur.executemany("UPDATE journeys SET time_to_prev_journey_fp = ? WHERE journey_id = ?", time_to_prev_journey)
        self.conn.commit()

    def initialize_database(self, journey_db_dir):
        assert not os.path.isfile(journey_db_dir)

        self.conn = sqlite3.connect(journey_db_dir)
        self._set_up_database()
        self._initialize_parameter_table()
        print("Database initialized!")
        if self.close_connection:
            self.conn.close()

    def _set_up_database(self):

        self.conn.execute('''CREATE TABLE IF NOT EXISTS parameters(
                     key TEXT UNIQUE,
                     value BLOB)''')
        if self.track_route:
            self.conn.execute('''CREATE TABLE IF NOT EXISTS journeys(
                         journey_id INTEGER PRIMARY KEY,
                         from_stop_I INT,
                         to_stop_I INT,
                         dep_time INT,
                         arr_time INT,
                         movement_duration INT,
                         route TEXT,
                         time_to_prev_journey_fp INT,
                         fastest_path INT)''')

            self.conn.execute('''CREATE TABLE IF NOT EXISTS connections(
                         journey_id INT,
                         from_stop_I INT,
                         to_stop_I INT,
                         dep_time INT,
                         arr_time INT,
                         trip_I INT,
                         seq INT,
                         leg_stops TEXT)''')
        else:
            self.conn.execute('''CREATE TABLE IF NOT EXISTS journeys(
                         journey_id INTEGER PRIMARY KEY,
                         from_stop_I INT,
                         to_stop_I INT,
                         dep_time INT,
                         arr_time INT,
                         n_boardings INT,
                         time_to_prev_journey_fp INT,
                         fastest_path INT)''')
        self.conn.commit()

    def _initialize_parameter_table(self):

        parameters = Parameters(self.conn)

        parameters["multiple_targets"] = self.multitarget_routing
        parameters["gtfs_dir"] = self.gtfs_dir
        for param in ["location_name",
                      "lat_median",
                      "lon_median",
                      "start_time_ut",
                      "end_time_ut",
                      "start_date",
                      "end_date"]:
            parameters[param] = self.gtfs_meta[param]

        for key, value in self.routing_params.items():
            parameters[key] = value
        self.conn.commit()

        """
        Parameter table contents:
        GTFS db identification data:
        -city/feed = location_name
        -lon_median, lat_median
        -end_time_ut, end_date, start_date, start_time_ut
        -checksum?
        -db directory

        Routing parameters:
        -transfer_margin
        -walking speed
        -walking distance
        -time/date
        -multiple targets (true/false)
        -
        """

    def create_indicies(self):
        # Next 3 lines are python 3.6 work-arounds again.
        self.conn.isolation_level = None  # former default of autocommit mode
        cur = self.conn.cursor()
        cur.execute('VACUUM;')
        self.conn.isolation_level = ''  # back to python default
        # end python3.6 workaround
        print("Analyzing...")
        cur.execute('ANALYZE')
        print("Indexing")
        cur = self.conn.cursor()
        cur.execute('CREATE INDEX IF NOT EXISTS idx_journeys_jid ON journeys (journey_id)')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_journeys_fid ON journeys (from_stop_I)')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_journeys_tid ON journeys (to_stop_I)')
        if self.track_route:
            cur.execute('CREATE INDEX IF NOT EXISTS idx_connections_jid ON connections (journey_id)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_connections_trid ON connections (trip_I)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_connections_fid ON connections (from_stop_I)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_connections_tid ON connections (to_stop_I)')
        self.conn.commit()
"""

    def add_fastest_path_column(self):
        cur = self.conn.cursor()
        # Select all distinct O-D pairs
        # For O-D pair in O-D pairs, create pareto-front
        cur.execute('SELECT from_stop_I, to_stop_I FROM journeys GROUP BY from_stop_I, to_stop_I')
        od_pairs = cur.fetchall()
        for pair in od_pairs:
            cur.execute('SELECT journey_id, arr_time, dep_time FROM journeys WHERE from_stop_I = ? AND to_stop_I = ? ORDER BY dep_time ASC', (pair[0], pair[1]))
            all_trips = cur.fetchall()
            pareto_trips = []
            cur_best_trips = []
            for trip in all_trips:
                is_dominated = False
                for best_trip in cur_best_trips:
                    if trip[1] > best_trip[1]:
                        is_dominated = True
                        break
                if is_dominated:
                    continue

                      """


class Parameters(object):
    """
    This provides dictionary protocol for updating parameters table, similar to GTFS metadata ("meta table").
    """

    def __init__(self, conn):
        self._conn = conn

    def __setitem__(self, key, value):
        self._conn.execute("INSERT OR REPLACE INTO parameters('key', 'value') VALUES (?, ?)", (key, value))
        self._conn.commit()

    def __getitem__(self, key):
        cur = self._conn.cursor()
        cur.execute("SELECT 'value' FROM parameters WHERE 'key'=?", (key,))
        val = cur.fetchone()
        if not val:
            raise KeyError("This journey db does not have parameter: %s" % key)
        return val[0]

    def __delitem__(self, key):
        self._conn.execute("DELETE FROM parameters WHERE 'key'=?", (key,))
        self._conn.commit()

    def __iter__(self):
        cur = self._conn.execute('SELECT key FROM parameters ORDER BY key')
        return (x[0] for x in cur)

    def __contains__(self, key):
        val = self._conn.execute('SELECT value FROM parameters WHERE key=?',
                                 (key,)).fetchone()
        return val is not None

    def get(self, key, default=None):
        val = self._conn.execute('SELECT value FROM parameters WHERE key=?',
                                 (key,)).fetchone()
        if not val:
            return default
        return val[0]

    def items(self):
        cur = self._conn.execute('SELECT key, value FROM parameters ORDER BY key')
        return cur

    def keys(self):
        cur = self._conn.execute('SELECT key FROM metadata ORDER BY key')
        return cur

    def values(self):
        cur = self._conn.execute('SELECT value FROM metadata ORDER BY key')
        return cur



