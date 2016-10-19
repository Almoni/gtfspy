from gtfspy.routing.plots import plot_temporal_distance_variation
from gtfspy.routing.node_profile import NodeProfile
from gtfspy.routing.label import Label

if __name__ == "__main__":
    profile = NodeProfile()
    profile.update_pareto_optimal_tuples(Label(departure_time=2 * 60, arrival_time_target=11 * 60))
    profile.update_pareto_optimal_tuples(Label(departure_time=20 * 60, arrival_time_target=25 * 60))
    profile.update_pareto_optimal_tuples(Label(departure_time=40 * 60, arrival_time_target=45 * 60))
    assert(len(profile.get_pareto_tuples()) == 3)
    plot_temporal_distance_variation(profile, start_time=0, end_time=60 * 60, show=True)



