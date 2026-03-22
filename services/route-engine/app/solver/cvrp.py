from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import structlog
from app.solver.state import BinState, TruckState

log = structlog.get_logger()


def solve_cvrp(
    bins:            list[BinState],
    trucks:          list[TruckState],
    distance_matrix: list[list[float]],
) -> dict[str, list[str]]:
    """
    Solve CVRP. Returns {truck_id: [sensor_id, ...]} in collection order.
    Index 0 in distance_matrix is the depot.
    """
    if not bins or not trucks:
        log.warning('cvrp.skipped', reason='no bins or no trucks')
        return {}

    n_locations = len(bins) + 1   # +1 for depot
    n_vehicles  = len(trucks)

    manager = pywrapcp.RoutingIndexManager(n_locations, n_vehicles, 0)
    routing = pywrapcp.RoutingModel(manager)

    def distance_cb(from_idx, to_idx):
        return int(distance_matrix[manager.IndexToNode(from_idx)]
                                  [manager.IndexToNode(to_idx)])

    transit_idx = routing.RegisterTransitCallback(distance_cb)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_idx)

    # Capacity: use fill_pct as demand, 300 = max demand per truck
    def demand_cb(from_idx):
        node = manager.IndexToNode(from_idx)
        return 0 if node == 0 else int(bins[node - 1].fill_pct)

    demand_idx = routing.RegisterUnaryTransitCallback(demand_cb)
    routing.AddDimensionWithVehicleCapacity(
        demand_idx, 0, [300] * n_vehicles, True, 'Capacity'
    )

    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )
    params.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )
    params.time_limit.seconds = 10

    solution = routing.SolveWithParameters(params)
    if not solution:
        log.warning('cvrp.no_solution', bins=len(bins), trucks=n_vehicles)
        return {}

    result = {}
    for v in range(n_vehicles):
        route = []
        idx   = routing.Start(v)
        while not routing.IsEnd(idx):
            node = manager.IndexToNode(idx)
            if node != 0:
                route.append(bins[node - 1].sensor_id)
            idx = solution.Value(routing.NextVar(idx))
        if route:
            result[trucks[v].truck_id] = route
            log.info('cvrp.route_assigned',
                     truck_id=trucks[v].truck_id,
                     stops=len(route))

    return result
