import math

from collections import defaultdict
from functools import cmp_to_key

import networkx as nx

from ..models.models import JoinOpt, LinkModel


class Join:
    def __init__(self, links: list[LinkModel], selected_fields: list[str]):
        self._links = links
        self.selected_fields = set(selected_fields)

    def check_if_selected(self, link: LinkModel):
        if (
            link.source_field_id in self.selected_fields
            or link.target_field_id in self.selected_fields
        ):
            return True
        return False

    def get_link_between_src_target(self, source, target):
        connected_asset = None
        fields_selected = False
        res = []
        for link in self._links:
            source_asset_id_in_link = link.source_asset_id in [source, target]
            target_asset_id_in_link = link.target_asset_id in [source, target]

            if source_asset_id_in_link and target_asset_id_in_link:
                ignore = not self.check_if_selected(link)
                connected_asset = (
                    link.target_asset_id
                    if target == link.target_asset_id
                    else link.source_asset_id
                )
                if not ignore:
                    fields_selected = True
                res.append({**link.model_dump(), "ignore": ignore})

        return res, connected_asset, fields_selected

    def _get_join_cndn(self, nodes_added, current_node):
        for prev_tbl in nodes_added[-1::-1]:
            if prev_tbl == current_node:
                continue
            res, connected_asset, fields_selected = self.get_link_between_src_target(
                current_node, prev_tbl
            )
            if not fields_selected:
                res = list(
                    map(lambda link: {**link, "ignore": False}, res)
                )  # Creates new dictionaries

            if len(res) > 0:
                return res, connected_asset
        return [], None

    @staticmethod
    def check_if_join_exists(graph: nx.MultiGraph, path_request: list[int]):
        graph_sizes = [
            len(c)
            for c in sorted(nx.connected_components(graph), key=len, reverse=True)
        ]

        if len(graph_sizes) == 1:
            return True

        path_request_set = set(path_request)
        path_request_len = len(path_request)
        sub_graphs = [graph.subgraph(c).copy() for c in nx.connected_components(graph)]
        link_found = False
        for _sub_graph in sub_graphs:
            current_nodes = set(_sub_graph.nodes)
            if len(current_nodes.intersection(path_request_set)) == path_request_len:
                link_found = True
                break

        return link_found

    @staticmethod
    def get_join_type(left, right):
        join_map = {
            (JoinOpt.all, JoinOpt.all): "full",
            (JoinOpt.all, JoinOpt.common): "left",
            (JoinOpt.common, JoinOpt.all): "right",
            (JoinOpt.common, JoinOpt.common): "inner",
        }
        return join_map.get((left, right), None)

    def get_table_node_weights(self, datasets_data: list[int], only_connected: bool = True):
        table_weight = defaultdict(list)
        table_connected_fields = defaultdict(list)
        table_connected_tables = defaultdict(set)

        for link in self._links:
            src_table = link.source_asset_id
            src_field = link.source_field_id
            target_table = link.target_asset_id
            target_field = link.source_field_id

            table_connected_fields[src_table].append(src_field)

            table_connected_fields[target_table].append(target_field)

            table_connected_tables[src_table].add(src_table)

            table_connected_tables[target_table].add(target_table)

        tables = list(table_connected_tables.keys())

        if not only_connected:
            tables.extend(datasets_data)

        for table in set(tables):
            if table in datasets_data:
                table_weight[table] = 0
                continue

            connected_field = table_connected_fields[table]

            set_connected_field = set(connected_field)

            table_weight[table] = len(connected_field) - len(set_connected_field)

        return dict(table_weight)

    @staticmethod
    def plot_graph(graph, path=None, draw_weight=False):
        import matplotlib.pyplot as plt
        import numpy as np

        pos = nx.spring_layout(
            graph, k=0.3 * 1 / np.sqrt(len(graph.nodes())), iterations=2, seed=5
        )

        # Draw the graph (without edge labels initially)
        plt.figure(3, figsize=(20, 20))

        # Draw nodes and edges
        nx.draw(
            graph,
            pos,
            with_labels=True,
            node_color="skyblue",
            node_size=2000,
            font_size=15,
            font_weight="bold",
            edge_color="gray",
        )

        if draw_weight:
            # Manually handle and draw edge labels for multiedges
            edge_labels = {}
            for u, v, key, data in graph.edges(data=True, keys=True):
                label = f"w={data['weight']}"
                if (u, v) not in edge_labels:
                    edge_labels[(u, v)] = []
                edge_labels[(u, v)].append((key, label))

            # Draw edge labels, considering multiple edges
            for (u, v), labels in edge_labels.items():
                for key, label in labels:
                    # For multiple edges, offset the label slightly to avoid overlap
                    x_offset = 0.05 * key  # offset for placing labels of multiple edges
                    y_offset = 0.05 * key
                    label_pos = (
                        (pos[u][0] + pos[v][0]) / 2 + x_offset,
                        (pos[u][1] + pos[v][1]) / 2 + y_offset,
                    )
                    plt.text(
                        label_pos[0],
                        label_pos[1],
                        label,
                        color="red",
                        fontsize=12,
                        ha="center",
                        va="center",
                    )

            # Manually draw node labels for their weights
            node_labels = nx.get_node_attributes(graph, "weight")
            for node, weight in node_labels.items():
                # Position the weight label slightly above the node
                label_pos = pos[node]
                plt.text(
                    label_pos[0],
                    label_pos[1] + 0.03,
                    f"{weight}",
                    fontsize=12,
                    ha="center",
                    va="bottom",
                    color="green",
                )

        if path:
            path_edges = list(zip(path, path[1:]))
            nx.draw_networkx_nodes(graph, pos, nodelist=path, node_color="y")
            nx.draw_networkx_edges(
                graph, pos, edgelist=path_edges, edge_color="y", width=10
            )
            plt.axis("equal")

        # Display the plot
        plt.title("Multigraph with Node and Edge Weights")
        plt.show()

    def generate_graph(self, datasets_data: list[int], only_connected: bool = True):
        graph = nx.MultiGraph()

        tables_weights = self.get_table_node_weights(datasets_data, only_connected)

        for table, weight in tables_weights.items():
            graph.add_node(table, weight=weight)

        # tables = set(sum([[i.source_asset_id, i.target_asset_id] for i in links], []))
        # graph.add_nodes_from(tables)

        for link in self._links:
            # relationship weight
            records_mapped = link.records_mapped
            source_count = link.source_count
            target_count = link.target_count
            if records_mapped == 0:
                records_mapped = 1
            if source_count == 0:
                source_count = 1
            if target_count == 0:
                target_count = 1

            source_mapped = min(link.source_count_distinct / records_mapped, 1)
            target_mapped = min(link.target_count_distinct / records_mapped, 1)

            source_uniqueness = min(link.source_count_distinct / source_count, 1)
            target_uniqueness = min(link.target_count_distinct / target_count, 1)

            # for many to many mapping
            uniqueness_weight = 5 - math.floor(max(source_uniqueness, target_uniqueness) * 4 + 1)

            # for mapping records
            source_mapped_weight = 5 - math.floor(
                source_mapped * 4 + 1
            )  # range from 5 to 1

            target_mapped_weight = 5 - math.floor(
                target_mapped * 4 + 1
            )  # range from 5 to 1

            link_weight = (
                tables_weights[link.target_asset_id]
                + source_mapped_weight
                + target_mapped_weight
                + uniqueness_weight
            )

            link_weight = min(link_weight, 10) + 1

            graph.add_edge(
                link.source_asset_id, link.target_asset_id, weight=link_weight
            )

        # self.plot_graph(graph)

        return graph

    @staticmethod
    def get_shortest_path(graph, source_node, target_nodes):
        _path = None
        _weight = None
        for _node in target_nodes:
            if _node == source_node:
                continue
            try:
                # _p = nx.shortest_path(graph, source=node_added, target=node)
                _p = nx.dijkstra_path(graph, source=_node, target=source_node)
                _wt = nx.dijkstra_path_length(graph, source=_node, target=source_node)
                if (
                    _path is None
                    or len(_path) > len(_p)
                    or _weight is None
                    or _weight < _wt
                ):
                    _path = _p
                    _weight = _wt
            except nx.exception.NetworkXNoPath:
                ...

        if _path is None:
            raise ValueError("Shortest join path not found")
        return _path, _weight

    def get_shortest_path_between_node_group(self, graph, source_nodes, target_nodes):
        _path = None
        _weight = None
        for source_node in source_nodes:
            for target_node in target_nodes:
                if target_node == source_node:
                    continue
                try:
                    # _p = nx.shortest_path(graph, source=node_added, target=node)
                    _p = nx.dijkstra_path(graph, source=source_node, target=target_node)
                    _wt = nx.dijkstra_path_length(
                        graph, source=source_node, target=target_node
                    )
                    if (
                        _path is None
                        or len(_path) > len(_p)
                        or _weight is None
                        or _weight < _wt
                    ):
                        _path = _p
                        _weight = _wt
                except nx.exception.NetworkXNoPath:
                    ...
        if _path is None:
            raise ValueError("Shortest join path not found")
        return _path, _weight

    @staticmethod
    def sort_path_request(datasets_data: list[int], join_opt: dict[str, JoinOpt] = {}):
        return sorted(
            datasets_data,
            key=cmp_to_key(
                lambda item1, item2: 1
                if (
                    join_opt.get(str(item1), JoinOpt.common) != JoinOpt.all
                    and join_opt.get(str(item2), JoinOpt.common) == JoinOpt.all
                )
                else -1
            ),
        )

    def get_join_json(
        self, datasets_data: list[int], join_opt: dict[str, JoinOpt] = {}
    ):
        links = self._links

        if len(links) <= 0 and len(datasets_data) <= 1:
            return {"0": {"dataset_id": datasets_data[0]}}
        
        graph = self.generate_graph(datasets_data)

        path_request = self.sort_path_request(datasets_data, join_opt)

        if not self.check_if_join_exists(graph, path_request):
            raise ValueError("Join path not found")

        join = {"0": {"dataset_id": path_request[0]}}

        cur_key = len(join.keys())

        first_table_opt = join_opt.get(str(path_request[0]), JoinOpt.all)

        nodes_added = [path_request[0]]
        remaining_nodes = [*path_request[1:]]

        while len(remaining_nodes) > 0:
            path, _ = self.get_shortest_path_between_node_group(
                graph, nodes_added, remaining_nodes
            )

            for path_node in path:
                if path_node in nodes_added:
                    continue

                fields, _ = self._get_join_cndn(nodes_added, path_node)

                # Used for linking tables
                if path_node not in path_request:
                    _first_table_opt = JoinOpt.all
                else:
                    _first_table_opt = first_table_opt

                second_table_opt = join_opt.get(str(path_node), JoinOpt.common)

                join_type = self.get_join_type(_first_table_opt, second_table_opt)

                join[str(cur_key)] = {
                    "dataset_id": path_node,
                    "join_type": join_type,
                    "fields": fields,
                }

                nodes_added.append(path_node)
                cur_key = cur_key + 1
                
                if path_node in path_request:
                    remaining_nodes.remove(path_node)

                if second_table_opt == JoinOpt.all:
                    first_table_opt = JoinOpt.all

        return join

    @classmethod
    def get_fields(cls, join_json: dict, links: list[LinkModel]):
        fields = set()

        if join_json:
            for join in join_json.values():
                for link in links:
                    if join["dataset_id"] == link.source_asset_id:
                        fields.add(link.source_field_id)
                    elif join["dataset_id"] == link.target_asset_id:
                        fields.add(link.target_field_id)

        return fields
