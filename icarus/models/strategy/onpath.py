"""Implementations of all on-path strategies"""
from __future__ import division
import random

import networkx as nx

from icarus.registry import register_strategy
from icarus.util import inheritdoc, path_links

from .base import Strategy

__all__ = [
       'Partition',
       'Edge',
       'LeaveCopyEverywhere',
       'LeaveCopyEverywherePacketLevel',
       'MaxReadQueueCapacityPacketLevel',
       'MaxWriteQueueCapacityPacketLevel',
       'LeaveCopyDown',
       'LeaveCopyDownPacketLevel',
       'ProbCache',
       'ProbCachePacketLevel',
       'CacheLessForMore',
       'CacheLessForMorePacketLevel',
       'RandomBernoulli',
       'RandomBernoulliPacketLevel',
       'RandomChoice',
       'RandomChoicePacketLevel'
           ]


@register_strategy('PARTITION')
class Partition(Strategy):
    """Partition caching strategy.

    In this strategy the network is divided into as many partitions as the number
    of caching nodes and each receiver is statically mapped to one and only one
    caching node. When a request is issued it is forwarded to the cache mapped
    to the receiver. In case of a miss the request is routed to the source and
    then returned to cache, which will store it and forward it back to the
    receiver.

    This requires median cache placement, which optimizes the placement of
    caches for this strategy.

    This strategy is normally used with a small number of caching nodes. This
    is the the behaviour normally adopted by Network CDN (NCDN). Google Global
    Cache (GGC) operates this way.
    """

    @inheritdoc(Strategy)
    def __init__(self, view, controller):
        super(Partition, self).__init__(view, controller)
        if 'cache_assignment' not in self.view.topology().graph:
            raise ValueError('The topology does not have cache assignment '
                             'information. Have you used the optimal median '
                             'cache assignment?')
        self.cache_assignment = self.view.topology().graph['cache_assignment']

    @inheritdoc(Strategy)
    def process_event(self, time, receiver, content, log):
        source = self.view.content_source(content)
        self.controller.start_session(time, receiver, content, log)
        cache = self.cache_assignment[receiver]
        self.controller.forward_request_path(receiver, cache)
        if not self.controller.get_content(cache):
            self.controller.forward_request_path(cache, source)
            self.controller.get_content(source)
            self.controller.forward_content_path(source, cache)
            self.controller.put_content(cache)
        self.controller.forward_content_path(cache, receiver)
        self.controller.end_session()


@register_strategy('EDGE')
class Edge(Strategy):
    """Edge caching strategy.

    In this strategy only a cache at the edge is looked up before forwarding
    a content request to the original source.

    In practice, this is like an LCE but it only queries the first cache it
    finds in the path. It is assumed to be used with a topology where each
    PoP has a cache but it simulates a case where the cache is actually further
    down the access network and it is not looked up for transit traffic passing
    through the PoP but only for PoP-originated requests.
    """

    @inheritdoc(Strategy)
    def __init__(self, view, controller):
        super(Edge, self).__init__(view, controller)

    @inheritdoc(Strategy)
    def process_event(self, time, receiver, content, log):
        # get all required data
        source = self.view.content_source(content)
        path = self.view.shortest_path(receiver, source)
        # Route requests to original source and queries caches on the path
        self.controller.start_session(time, receiver, content, log)
        edge_cache = None
        for u, v in path_links(path):
            self.controller.forward_request_hop(u, v)
            if self.view.has_cache(v):
                edge_cache = v
                if self.controller.get_content(v):
                    serving_node = v
                else:
                    # Cache miss, get content from source
                    self.controller.forward_request_path(v, source)
                    self.controller.get_content(source)
                    serving_node = source
                break
        else:
            # No caches on the path at all, get it from source
            self.controller.get_content(v)
            serving_node = v

        # Return content
        path = list(reversed(self.view.shortest_path(receiver, serving_node)))
        self.controller.forward_content_path(serving_node, receiver, path)
        if serving_node == source:
            self.controller.put_content(edge_cache)
        self.controller.end_session()


@register_strategy('MWQC_PKT_LEVEL')
class MaxWriteQueueCapacityPacketLevel(Strategy):
    """MaxWriteQueueCapacity (MWQC) packet-level strategy.

    This strategy chooses the node along the path with the biggest write-queue capacity
    and cache.
    """
    @inheritdoc(Strategy)
    def __init__(self, view, controller, **kwargs):
        super(MaxWriteQueueCapacityPacketLevel, self).__init__(view, controller)

    @inheritdoc(Strategy)
    def process_event(self, time, receiver, content, node, flow, pkt_type, log):
        # get all required data
        # Route requests to original source and queries caches on the path
        if pkt_type == 'Request':
            if node == receiver:
                self.controller.start_flow_session(time, receiver, content, flow, log)
            source = self.view.content_source(content)
            if node == source:
                path = self.view.shortest_path(node, receiver)
                link_delay = self.view.link_delay(node, path[1])
                t_event = time + link_delay
                self.controller.forward_request_hop_flow(node, path[1], flow, log)
                self.controller.add_event({'t_event': t_event, 'receiver': receiver, 'content': content, 'node': path[1], 'flow': flow, 'pkt_type': 'Data', 'log': log} )
                return
            if (self.view.has_cache(node) and self.view.get_node_read_queue_index(node) < self.view.get_read_queue_size_limit()):     
                if self.controller.get_content_flow(node, content, flow, log):
                    self.controller.push_node_read_queue(node, flow)
                    idx = self.view.get_node_read_queue_index(node)
                    t_event = time + idx * self.view.get_single_cache_read_penalty()
                    self.controller.add_event({'t_event': t_event, 'receiver': receiver, 'content': content, 'node': node, 'flow': flow, 'pkt_type': 'ReadComplete', 'log': log})
                    return

            # no cache get, forward request to the next node
            path = self.view.shortest_path(node, source)
            delay = self.view.link_delay(node, path[1])
            t_event = time + delay
            self.controller.forward_request_hop_flow(node, path[1], flow, log)
            self.controller.add_event({'t_event': t_event, 'receiver': receiver, 'content': content, 'node': path[1], 'flow': flow, 'pkt_type': 'Request', 'log': log} )

        elif pkt_type == 'Data':
            if node == receiver:
                self.controller.end_flow_session(flow, log)
            else:
                # pass it down to the receiver
                path = self.view.shortest_path(node, receiver)
                self.controller.forward_content_hop_flow(node, path[1], flow, log)
                delay = self.view.link_delay(node, path[1])
                t_event = time + delay
                self.controller.add_event({'t_event': t_event, 'receiver': receiver, 'content': content, 'node': path[1], 'flow': flow, 'pkt_type': 'Data', 'log': log})
        
        elif pkt_type == 'ReadComplete':
            # cache read complete, send the content back to the receiver
            self.controller.pop_node_read_queue(node, flow)
            path = self.view.shortest_path(node, receiver)
            link_delay = self.view.link_delay(node, path[1])
            t_event = time + link_delay
            self.controller.forward_request_hop_flow(node, path[1], flow, log)
            self.controller.add_event({'t_event': t_event, 'receiver': receiver, 'content': content, 'node': path[1], 'flow': flow, 'pkt_type': 'Data', 'log': log} )
            
            # select the node with largest read_queue_capacity and write the content
            chosen_node = None
            max_capacity = 0
            for hop in range(1, len(path)):
                # u = path[hop - 1]
                v = path[hop]
                if v != receiver and self.view.has_cache(v):
                    current_node_write_capacity = self.view.get_write_queue_size_limit() - self.view.get_node_write_queue_index(v)
                    if current_node_write_capacity >= max_capacity:
                        max_capacity = current_node_write_capacity
                        chosen_node = v

            if chosen_node:
                # current node write is not full, write the content
                if self.view.get_node_write_queue_index(node) < self.view.get_write_queue_size_limit():
                    self.controller.push_node_write_queue(chosen_node, flow)
                    idx = self.view.get_node_write_queue_index(chosen_node)
                    t_event = time + idx * self.view.get_single_cache_write_penalty()
                    self.controller.add_event({'t_event': t_event, 'receiver': receiver, 'content': content, 'node': chosen_node, 'flow': flow, 'pkt_type': 'WriteComplete', 'log': log})

        elif pkt_type == 'WriteComplete':
            self.controller.pop_node_write_queue(node, flow)
            self.controller.put_content_flow(node, content, flow)

        else:
            raise ValueError('Invalid packet type')


@register_strategy('MRQC_PKT_LEVEL')
class MaxReadQueueCapacityPacketLevel(Strategy):
    """MaxReadQueueCapacity (MRQC) packet-level strategy.

    This strategy chooses the node along the path with the biggest read-queue capacity
    and cache.
    """
    @inheritdoc(Strategy)
    def __init__(self, view, controller, **kwargs):
        super(MaxReadQueueCapacityPacketLevel, self).__init__(view, controller)

    @inheritdoc(Strategy)
    def process_event(self, time, receiver, content, node, flow, pkt_type, log):
        # get all required data
        # Route requests to original source and queries caches on the path
        if pkt_type == 'Request':
            if node == receiver:
                self.controller.start_flow_session(time, receiver, content, flow, log)
            source = self.view.content_source(content)
            if node == source:
                path = self.view.shortest_path(node, receiver)
                link_delay = self.view.link_delay(node, path[1])
                t_event = time + link_delay
                self.controller.forward_request_hop_flow(node, path[1], flow, log)
                self.controller.add_event({'t_event': t_event, 'receiver': receiver, 'content': content, 'node': path[1], 'flow': flow, 'pkt_type': 'Data', 'log': log} )
                return
            if (self.view.has_cache(node) and self.view.get_node_read_queue_index(node) < self.view.get_read_queue_size_limit()):     
                if self.controller.get_content_flow(node, content, flow, log):
                    self.controller.push_node_read_queue(node, flow)
                    idx = self.view.get_node_read_queue_index(node)
                    t_event = time + idx * self.view.get_single_cache_read_penalty()
                    self.controller.add_event({'t_event': t_event, 'receiver': receiver, 'content': content, 'node': node, 'flow': flow, 'pkt_type': 'ReadComplete', 'log': log})
                    return

            # no cache get, forward request to the next node
            path = self.view.shortest_path(node, source)
            delay = self.view.link_delay(node, path[1])
            t_event = time + delay
            self.controller.forward_request_hop_flow(node, path[1], flow, log)
            self.controller.add_event({'t_event': t_event, 'receiver': receiver, 'content': content, 'node': path[1], 'flow': flow, 'pkt_type': 'Request', 'log': log} )

        elif pkt_type == 'Data':
            if node == receiver:
                self.controller.end_flow_session(flow, log)
            else:
                # pass it down to the receiver
                path = self.view.shortest_path(node, receiver)
                self.controller.forward_content_hop_flow(node, path[1], flow, log)
                delay = self.view.link_delay(node, path[1])
                t_event = time + delay
                self.controller.add_event({'t_event': t_event, 'receiver': receiver, 'content': content, 'node': path[1], 'flow': flow, 'pkt_type': 'Data', 'log': log})
        
        elif pkt_type == 'ReadComplete':
            # cache read complete, send the content back to the receiver
            self.controller.pop_node_read_queue(node, flow)
            path = self.view.shortest_path(node, receiver)
            link_delay = self.view.link_delay(node, path[1])
            t_event = time + link_delay
            self.controller.forward_request_hop_flow(node, path[1], flow, log)
            self.controller.add_event({'t_event': t_event, 'receiver': receiver, 'content': content, 'node': path[1], 'flow': flow, 'pkt_type': 'Data', 'log': log} )
            
            # select the node with largest read_queue_capacity and write the content
            chosen_node = None
            max_capacity = 0
            for hop in range(1, len(path)):
                # u = path[hop - 1]
                v = path[hop]
                if v != receiver and self.view.has_cache(v):
                    current_node_read_capacity = self.view.get_read_queue_size_limit() - self.view.get_node_read_queue_index(v)
                    if current_node_read_capacity >= max_capacity:
                        max_capacity = current_node_read_capacity
                        chosen_node = v

            if chosen_node:
                # current node write is not full, write the content
                if self.view.get_node_write_queue_index(node) < self.view.get_write_queue_size_limit():
                    self.controller.push_node_write_queue(chosen_node, flow)
                    idx = self.view.get_node_write_queue_index(chosen_node)
                    t_event = time + idx * self.view.get_single_cache_write_penalty()
                    self.controller.add_event({'t_event': t_event, 'receiver': receiver, 'content': content, 'node': chosen_node, 'flow': flow, 'pkt_type': 'WriteComplete', 'log': log})

        elif pkt_type == 'WriteComplete':
            self.controller.pop_node_write_queue(node, flow)
            self.controller.put_content_flow(node, content, flow)

        else:
            raise ValueError('Invalid packet type')


@register_strategy('LCE_PKT_LEVEL')
class LeaveCopyEverywherePacketLevel(Strategy):
    """Leave Copy Everywhere (LCE) packet-level strategy.

    In this strategy a copy of a content is replicated at any cache on the
    path between serving node and receiver.
    """

    @inheritdoc(Strategy)
    def __init__(self, view, controller, **kwargs):
        super(LeaveCopyEverywherePacketLevel, self).__init__(view, controller)

    @inheritdoc(Strategy)
    def process_event(self, time, receiver, content, node, flow, pkt_type, log):
        # get all required data
        # Route requests to original source and queries caches on the path
        if pkt_type == 'Request':
            if node == receiver:
                self.controller.start_flow_session(time, receiver, content, flow, log)
            source = self.view.content_source(content)
            if node == source:
                path = self.view.shortest_path(node, receiver)
                link_delay = self.view.link_delay(node, path[1])
                t_event = time + link_delay
                self.controller.forward_request_hop_flow(node, path[1], flow, log)
                self.controller.add_event({'t_event': t_event, 'receiver': receiver, 'content': content, 'node': path[1], 'flow': flow, 'pkt_type': 'Data', 'log': log} )
                return
            if self.view.has_cache(node):
                self.controller.query_content_flow(node, content, flow, log)
            if self.view.has_cache(node) and self.view.get_node_read_queue_index(node) < self.view.get_read_queue_size_limit():     
                if self.controller.get_content_flow(node, content, flow, log):
                    self.controller.push_node_read_queue(node, flow)
                    idx = self.view.get_node_read_queue_index(node)
                    t_event = time + idx * self.view.get_single_cache_read_penalty()
                    self.controller.add_event({'t_event': t_event, 'receiver': receiver, 'content': content, 'node': node, 'flow': flow, 'pkt_type': 'ReadComplete', 'log': log})
                    return

            # no cache get, forward request to the next node
            path = self.view.shortest_path(node, source)
            delay = self.view.link_delay(node, path[1])
            t_event = time + delay
            self.controller.forward_request_hop_flow(node, path[1], flow, log)
            self.controller.add_event({'t_event': t_event, 'receiver': receiver, 'content': content, 'node': path[1], 'flow': flow, 'pkt_type': 'Request', 'log': log} )

        elif pkt_type == 'Data':
            if node == receiver:
                self.controller.end_flow_session(flow, log)
            else:
                # current node write is not full, write the content
                if self.view.get_node_write_queue_index(node) < self.view.get_write_queue_size_limit():
                    self.controller.push_node_write_queue(node, flow)
                    idx = self.view.get_node_write_queue_index(node)
                    t_event = time + idx * self.view.get_single_cache_write_penalty()
                    self.controller.add_event({'t_event': t_event, 'receiver': receiver, 'content': content, 'node': node, 'flow': flow, 'pkt_type': 'WriteComplete', 'log': log})

                # no matter written or not, pass it down to the receiver
                path = self.view.shortest_path(node, receiver)
                self.controller.forward_content_hop_flow(node, path[1], flow, log)
                delay = self.view.link_delay(node, path[1])
                t_event = time + delay
                self.controller.add_event({'t_event': t_event, 'receiver': receiver, 'content': content, 'node': path[1], 'flow': flow, 'pkt_type': 'Data', 'log': log})
        
        elif pkt_type == 'ReadComplete':
            # cache read complete, send the content back to the receiver
            self.controller.pop_node_read_queue(node, flow)
            path = self.view.shortest_path(node, receiver)
            link_delay = self.view.link_delay(node, path[1])
            t_event = time + link_delay
            self.controller.forward_request_hop_flow(node, path[1], flow, log)
            self.controller.add_event({'t_event': t_event, 'receiver': receiver, 'content': content, 'node': path[1], 'flow': flow, 'pkt_type': 'Data', 'log': log} )
            

        elif pkt_type == 'WriteComplete':
            self.controller.pop_node_write_queue(node, flow)
            self.controller.put_content_flow(node, content, flow)

        else:
            raise ValueError('Invalid packet type')

@register_strategy('LCE')
class LeaveCopyEverywhere(Strategy):
    """Leave Copy Everywhere (LCE) strategy.

    In this strategy a copy of a content is replicated at any cache on the
    path between serving node and receiver.
    """

    @inheritdoc(Strategy)
    def __init__(self, view, controller, **kwargs):
        super(LeaveCopyEverywhere, self).__init__(view, controller)

    @inheritdoc(Strategy)
    def process_event(self, time, receiver, content, log):
        # get all required data
        source = self.view.content_source(content)
        path = self.view.shortest_path(receiver, source)
        # Route requests to original source and queries caches on the path
        self.controller.start_session(time, receiver, content, log)
        for u, v in path_links(path):
            self.controller.forward_request_hop(u, v)
            if self.view.has_cache(v):
                if self.controller.get_content(v):
                    serving_node = v
                    break
            # No cache hits, get content from source
            self.controller.get_content(v)
            serving_node = v
        # Return content
        path = list(reversed(self.view.shortest_path(receiver, serving_node)))
        for u, v in path_links(path):
            self.controller.forward_content_hop(u, v)
            if self.view.has_cache(v):
                # insert content
                self.controller.put_content(v)
        self.controller.end_session()

@register_strategy('LCD_PKT_LEVEL')
class LeaveCopyDownPacketLevel(Strategy):

    @inheritdoc(Strategy)
    def __init__(self, view, controller, **kwargs):
        super(LeaveCopyDownPacketLevel, self).__init__(view, controller)

    @inheritdoc(Strategy)
    def process_event(self, time, receiver, content, node, flow, pkt_type, log):
        # get all required data
        # Route requests to original source and queries caches on the path
        if pkt_type == 'Request':
            if node == receiver:
                self.controller.start_flow_session(time, receiver, content, flow, log)
            source = self.view.content_source(content)
            if node == source:
                path = self.view.shortest_path(node, receiver)
                link_delay = self.view.link_delay(node, path[1])
                t_event = time + link_delay
                self.controller.forward_request_hop_flow(node, path[1], flow, log)
                self.controller.add_event({'t_event': t_event, 'receiver': receiver, 'content': content, 'node': path[1], 'flow': flow, 'pkt_type': 'Data', 'log': log} )
                return
            if self.view.has_cache(node):
                self.controller.query_content_flow(node, content, flow, log)
            if (self.view.has_cache(node) and self.view.get_node_read_queue_index(node) < self.view.get_read_queue_size_limit()):
                if self.controller.get_content_flow(node, content, flow, log):
                    self.controller.push_node_read_queue(node, flow)
                    idx = self.view.get_node_read_queue_index(node)
                    t_event = time + idx * self.view.get_single_cache_read_penalty()
                    self.controller.add_event({'t_event': t_event, 'receiver': receiver, 'content': content, 'node': node, 'flow': flow, 'pkt_type': 'ReadComplete', 'log': log})
                    return

            # no cache get, forward request to the next node
            path = self.view.shortest_path(node, source)
            delay = self.view.link_delay(node, path[1])
            t_event = time + delay
            self.controller.forward_request_hop_flow(node, path[1], flow, log)
            self.controller.add_event({'t_event': t_event, 'receiver': receiver, 'content': content, 'node': path[1], 'flow': flow, 'pkt_type': 'Request', 'log': log} )
    
        elif pkt_type == 'Data':
            if node == receiver:
                self.controller.end_flow_session(flow, log)
            else:
                # no matter written or not, pass it down to the receiver
                path = self.view.shortest_path(node, receiver)
                self.controller.forward_content_hop_flow(node, path[1], flow, log)
                delay = self.view.link_delay(node, path[1])
                t_event = time + delay
                self.controller.add_event({'t_event': t_event, 'receiver': receiver, 'content': content, 'node': path[1], 'flow': flow, 'pkt_type': 'Data', 'log': log})

        elif pkt_type == 'ReadComplete':
            # cache read complete, send the content back to the receiver
            self.controller.pop_node_read_queue(node, flow)
            path = self.view.shortest_path(node, receiver)
            link_delay = self.view.link_delay(node, path[1])
            t_event = time + link_delay
            self.controller.forward_request_hop_flow(node, path[1], flow, log)
            self.controller.add_event({'t_event': t_event, 'receiver': receiver, 'content': content, 'node': path[1], 'flow': flow, 'pkt_type': 'Data', 'log': log} )
            
            # make the node next level(but not receiver) cache the current content
            if path[1] != receiver:
                # current node write is not full, write the content
                if self.view.get_node_write_queue_index(node) < self.view.get_write_queue_size_limit():
                    self.controller.push_node_write_queue(path[1], flow)
                    idx = self.view.get_node_write_queue_index(path[1])
                    t_event = time + idx * self.view.get_single_cache_write_penalty()
                    self.controller.add_event({'t_event': t_event, 'receiver': receiver, 'content': content, 'node': path[1], 'flow': flow, 'pkt_type': 'WriteComplete', 'log': log})

        elif pkt_type == 'WriteComplete':
            self.controller.pop_node_write_queue(node, flow)
            self.controller.put_content_flow(node, content, flow)

        else:
            raise ValueError('Invalid packet type')


@register_strategy('LCD')
class LeaveCopyDown(Strategy):
    """Leave Copy Down (LCD) strategy.

    According to this strategy, one copy of a content is replicated only in
    the caching node you hop away from the serving node in the direction of
    the receiver. This strategy is described in [2]_.

    Rereferences
    ------------
    ..[1] N. Laoutaris, H. Che, i. Stavrakakis, The LCD interconnection of LRU
          caches and its analysis.
          Available: http://cs-people.bu.edu/nlaout/analysis_PEVA.pdf
    """

    @inheritdoc(Strategy)
    def __init__(self, view, controller, **kwargs):
        super(LeaveCopyDown, self).__init__(view, controller)

    @inheritdoc(Strategy)
    def process_event(self, time, receiver, content, log):
        # get all required data
        source = self.view.content_source(content)
        path = self.view.shortest_path(receiver, source)
        # Route requests to original source and queries caches on the path
        self.controller.start_session(time, receiver, content, log)
        for u, v in path_links(path):
            self.controller.forward_request_hop(u, v)
            if self.view.has_cache(v):
                if self.controller.get_content(v):
                    serving_node = v
                    break
        else:
            # No cache hits, get content from source
            self.controller.get_content(v)
            serving_node = v
        # Return content
        path = list(reversed(self.view.shortest_path(receiver, serving_node)))
        # Leave a copy of the content only in the cache one level down the hit
        # caching node
        copied = False
        for u, v in path_links(path):
            self.controller.forward_content_hop(u, v)
            if not copied and v != receiver and self.view.has_cache(v):
                self.controller.put_content(v)
                copied = True
        self.controller.end_session()


@register_strategy('PROB_CACHE_PKT_LEVEL')
class ProbCachePacketLevel(Strategy):

    @inheritdoc(Strategy)
    def __init__(self, view, controller, t_tw=10):
        super(ProbCachePacketLevel, self).__init__(view, controller)
        self.t_tw = t_tw
        self.cache_size = view.cache_nodes(size=True)

    @inheritdoc(Strategy)
    def process_event(self, time, receiver, content, node, flow, pkt_type, log):
        # get all required data
        # Route requests to original source and queries caches on the path
        if pkt_type == 'Request':
            if node == receiver:
                self.controller.start_flow_session(time, receiver, content, flow, log)
            source = self.view.content_source(content)
            if node == source:
                path = self.view.shortest_path(node, receiver)
                link_delay = self.view.link_delay(node, path[1])
                t_event = time + link_delay
                self.controller.forward_request_hop_flow(node, path[1], flow, log)
                self.controller.add_event({'t_event': t_event, 'receiver': receiver, 'content': content, 'node': path[1], 'flow': flow, 'pkt_type': 'Data', 'log': log} )
                return
            if self.view.has_cache(node):
                self.controller.query_content_flow(node, content, flow, log)
            if (self.view.has_cache(node) and self.view.get_node_read_queue_index(node) < self.view.get_read_queue_size_limit()):
                if self.controller.get_content_flow(node, content, flow, log):
                    self.controller.push_node_read_queue(node, flow)
                    idx = self.view.get_node_read_queue_index(node)
                    t_event = time + idx * self.view.get_single_cache_read_penalty()
                    self.controller.add_event({'t_event': t_event, 'receiver': receiver, 'content': content, 'node': node, 'flow': flow, 'pkt_type': 'ReadComplete', 'log': log})
                    return

            # no cache get, forward request to the next node
            path = self.view.shortest_path(node, source)
            delay = self.view.link_delay(node, path[1])
            t_event = time + delay
            self.controller.forward_request_hop_flow(node, path[1], flow, log)
            self.controller.add_event({'t_event': t_event, 'receiver': receiver, 'content': content, 'node': path[1], 'flow': flow, 'pkt_type': 'Request', 'log': log} )
    
        elif pkt_type == 'Data':
            if node == receiver:
                self.controller.end_flow_session(flow, log)
            else:
                # no matter written or not, pass it down to the receiver
                path = self.view.shortest_path(node, receiver)
                self.controller.forward_content_hop_flow(node, path[1], flow, log)
                delay = self.view.link_delay(node, path[1])
                t_event = time + delay
                self.controller.add_event({'t_event': t_event, 'receiver': receiver, 'content': content, 'node': path[1], 'flow': flow, 'pkt_type': 'Data', 'log': log})

        elif pkt_type == 'ReadComplete':
            # cache read complete, send the content back to the receiver
            self.controller.pop_node_read_queue(node, flow)
            path = self.view.shortest_path(node, receiver)
            link_delay = self.view.link_delay(node, path[1])
            t_event = time + link_delay
            self.controller.forward_request_hop_flow(node, path[1], flow, log)
            self.controller.add_event({'t_event': t_event, 'receiver': receiver, 'content': content, 'node': path[1], 'flow': flow, 'pkt_type': 'Data', 'log': log} )
            
            # select prob_cache and write the content
            c = len([node for node in path if self.view.has_cache(node)])
            x = 0.0
            for hop in range(1, len(path)):
                # u = path[hop - 1]
                v = path[hop]
                N = sum([self.cache_size[n] for n in path[hop - 1:]
                        if n in self.cache_size])
                if v in self.cache_size:
                    x += 1
                if v != receiver and v in self.cache_size:
                    # The (x/c) factor raised to the power of "c" according to the
                    # extended version of ProbCache published in IEEE TPDS
                    prob_cache = float(N) / (self.t_tw * self.cache_size[v]) * (x / c) ** c
                    if random.random() < prob_cache:
                        # current node write is not full, write the content
                        if self.view.get_node_write_queue_index(node) < self.view.get_write_queue_size_limit():
                            self.controller.push_node_write_queue(v, flow)
                            idx = self.view.get_node_write_queue_index(v)
                            t_event = time + idx * self.view.get_single_cache_write_penalty()
                            self.controller.add_event({'t_event': t_event, 'receiver': receiver, 'content': content, 'node': v, 'flow': flow, 'pkt_type': 'WriteComplete', 'log': log})

        elif pkt_type == 'WriteComplete':
            self.controller.pop_node_write_queue(node, flow)
            self.controller.put_content_flow(node, content, flow)

        else:
            raise ValueError('Invalid packet type')

@register_strategy('PROB_CACHE')
class ProbCache(Strategy):
    """ProbCache strategy [3]_

    This strategy caches content objects probabilistically on a path with a
    probability depending on various factors, including distance from source
    and destination and caching space available on the path.

    This strategy was originally proposed in [2]_ and extended in [3]_. This
    class implements the extended version described in [3]_. In the extended
    version of ProbCache the :math`x/c` factor of the ProbCache equation is
    raised to the power of :math`c`.

    References
    ----------
    ..[2] I. Psaras, W. Chai, G. Pavlou, Probabilistic In-Network Caching for
          Information-Centric Networks, in Proc. of ACM SIGCOMM ICN '12
          Available: http://www.ee.ucl.ac.uk/~uceeips/prob-cache-icn-sigcomm12.pdf
    ..[3] I. Psaras, W. Chai, G. Pavlou, In-Network Cache Management and
          Resource Allocation for Information-Centric Networks, IEEE
          Transactions on Parallel and Distributed Systems, 22 May 2014
          Available: http://doi.ieeecomputersociety.org/10.1109/TPDS.2013.304
    """

    @inheritdoc(Strategy)
    def __init__(self, view, controller, t_tw=10):
        super(ProbCache, self).__init__(view, controller)
        self.t_tw = t_tw
        self.cache_size = view.cache_nodes(size=True)

    @inheritdoc(Strategy)
    def process_event(self, time, receiver, content, log):
        # get all required data
        source = self.view.content_source(content)
        path = self.view.shortest_path(receiver, source)
        # Route requests to original source and queries caches on the path
        self.controller.start_session(time, receiver, content, log)
        for hop in range(1, len(path)):
            u = path[hop - 1]
            v = path[hop]
            self.controller.forward_request_hop(u, v)
            if self.view.has_cache(v):
                if self.controller.get_content(v):
                    serving_node = v
                    break
        else:
            # No cache hits, get content from source
            self.controller.get_content(v)
            serving_node = v
        # Return content
        path = list(reversed(self.view.shortest_path(receiver, serving_node)))
        c = len([node for node in path if self.view.has_cache(node)])
        x = 0.0
        for hop in range(1, len(path)):
            u = path[hop - 1]
            v = path[hop]
            N = sum([self.cache_size[n] for n in path[hop - 1:]
                     if n in self.cache_size])
            if v in self.cache_size:
                x += 1
            self.controller.forward_content_hop(u, v)
            if v != receiver and v in self.cache_size:
                # The (x/c) factor raised to the power of "c" according to the
                # extended version of ProbCache published in IEEE TPDS
                prob_cache = float(N) / (self.t_tw * self.cache_size[v]) * (x / c) ** c
                if random.random() < prob_cache:
                    self.controller.put_content(v)
        self.controller.end_session()


@register_strategy('CL4M_PKT_LEVEL')
class CacheLessForMorePacketLevel(Strategy):
    """Cache less for more strategy [4]_.

    This strategy caches items only once in the delivery path, precisely in the
    node with the greatest betweenness centrality (i.e., that is traversed by
    the greatest number of shortest paths). If the argument *use_ego_betw* is
    set to *True* then the betweenness centrality of the ego-network is used
    instead.

    References
    ----------
    ..[4] W. Chai, D. He, I. Psaras, G. Pavlou, Cache Less for More in
          Information-centric Networks, in IFIP NETWORKING '12
          Available: http://www.ee.ucl.ac.uk/~uceeips/centrality-networking12.pdf
    """

    @inheritdoc(Strategy)
    def __init__(self, view, controller, use_ego_betw=False, **kwargs):
        super(CacheLessForMorePacketLevel, self).__init__(view, controller)
        topology = view.topology()
        if use_ego_betw:
            self.betw = dict((v, nx.betweenness_centrality(nx.ego_graph(topology, v))[v])
                             for v in topology.nodes())
        else:
            self.betw = nx.betweenness_centrality(topology)
    
    @inheritdoc(Strategy)
    def process_event(self, time, receiver, content, node, flow, pkt_type, log):
        # get all required data
        # Route requests to original source and queries caches on the path
        if pkt_type == 'Request':
            if node == receiver:
                self.controller.start_flow_session(time, receiver, content, flow, log)
            source = self.view.content_source(content)
            if node == source:
                path = self.view.shortest_path(node, receiver)
                link_delay = self.view.link_delay(node, path[1])
                t_event = time + link_delay
                self.controller.forward_request_hop_flow(node, path[1], flow, log)
                self.controller.add_event({'t_event': t_event, 'receiver': receiver, 'content': content, 'node': path[1], 'flow': flow, 'pkt_type': 'Data', 'log': log} )
                return
            if self.view.has_cache(node):
                self.controller.query_content_flow(node, content, flow, log)
            if (self.view.has_cache(node) and self.view.get_node_read_queue_index(node) < self.view.get_read_queue_size_limit()):
                if self.controller.get_content_flow(node, content, flow, log):
                    self.controller.push_node_read_queue(node, flow)
                    idx = self.view.get_node_read_queue_index(node)
                    t_event = time + idx * self.view.get_single_cache_read_penalty()
                    self.controller.add_event({'t_event': t_event, 'receiver': receiver, 'content': content, 'node': node, 'flow': flow, 'pkt_type': 'ReadComplete', 'log': log})
                    return

            # no cache get, forward request to the next node
            path = self.view.shortest_path(node, source)
            delay = self.view.link_delay(node, path[1])
            t_event = time + delay
            self.controller.forward_request_hop_flow(node, path[1], flow, log)
            self.controller.add_event({'t_event': t_event, 'receiver': receiver, 'content': content, 'node': path[1], 'flow': flow, 'pkt_type': 'Request', 'log': log} )
    
        elif pkt_type == 'Data':
            if node == receiver:
                self.controller.end_flow_session(flow, log)
            else:
                # no matter written or not, pass it down to the receiver
                path = self.view.shortest_path(node, receiver)
                self.controller.forward_content_hop_flow(node, path[1], flow, log)
                delay = self.view.link_delay(node, path[1])
                t_event = time + delay
                self.controller.add_event({'t_event': t_event, 'receiver': receiver, 'content': content, 'node': path[1], 'flow': flow, 'pkt_type': 'Data', 'log': log})

        elif pkt_type == 'ReadComplete':
            # cache read complete, send the content back to the receiver
            self.controller.pop_node_read_queue(node, flow)
            path = self.view.shortest_path(node, receiver)
            link_delay = self.view.link_delay(node, path[1])
            t_event = time + link_delay
            self.controller.forward_request_hop_flow(node, path[1], flow, log)
            self.controller.add_event({'t_event': t_event, 'receiver': receiver, 'content': content, 'node': path[1], 'flow': flow, 'pkt_type': 'Data', 'log': log} )
            
            # select cache and write the content
            max_betw = -1
            designated_cache = None
            for v in path[1:]:
                if self.view.has_cache(v):
                    if self.betw[v] >= max_betw:
                        max_betw = self.betw[v]
                        designated_cache = v
            if designated_cache:
                # current node write is not full, write the content
                if self.view.get_node_write_queue_index(node) < self.view.get_write_queue_size_limit():
                    self.controller.push_node_write_queue(designated_cache, flow)
                    idx = self.view.get_node_write_queue_index(designated_cache)
                    t_event = time + idx * self.view.get_single_cache_write_penalty()
                    self.controller.add_event({'t_event': t_event, 'receiver': receiver, 'content': content, 'node': designated_cache, 'flow': flow, 'pkt_type': 'WriteComplete', 'log': log})

        elif pkt_type == 'WriteComplete':
            self.controller.pop_node_write_queue(node, flow)
            self.controller.put_content_flow(node, content, flow)

        else:
            raise ValueError('Invalid packet type')


@register_strategy('CL4M')
class CacheLessForMore(Strategy):
    """Cache less for more strategy [4]_.

    This strategy caches items only once in the delivery path, precisely in the
    node with the greatest betweenness centrality (i.e., that is traversed by
    the greatest number of shortest paths). If the argument *use_ego_betw* is
    set to *True* then the betweenness centrality of the ego-network is used
    instead.

    References
    ----------
    ..[4] W. Chai, D. He, I. Psaras, G. Pavlou, Cache Less for More in
          Information-centric Networks, in IFIP NETWORKING '12
          Available: http://www.ee.ucl.ac.uk/~uceeips/centrality-networking12.pdf
    """

    @inheritdoc(Strategy)
    def __init__(self, view, controller, use_ego_betw=False, **kwargs):
        super(CacheLessForMore, self).__init__(view, controller)
        topology = view.topology()
        if use_ego_betw:
            self.betw = dict((v, nx.betweenness_centrality(nx.ego_graph(topology, v))[v])
                             for v in topology.nodes())
        else:
            self.betw = nx.betweenness_centrality(topology)

    @inheritdoc(Strategy)
    def process_event(self, time, receiver, content, log):
        # get all required data
        source = self.view.content_source(content)
        path = self.view.shortest_path(receiver, source)
        # Route requests to original source and queries caches on the path
        self.controller.start_session(time, receiver, content, log)
        for u, v in path_links(path):
            self.controller.forward_request_hop(u, v)
            if self.view.has_cache(v):
                if self.controller.get_content(v):
                    serving_node = v
                    break
        # No cache hits, get content from source
        else:
            self.controller.get_content(v)
            serving_node = v
        # Return content
        path = list(reversed(self.view.shortest_path(receiver, serving_node)))
        # get the cache with maximum betweenness centrality
        # if there are more than one cache with max betw then pick the one
        # closer to the receiver
        max_betw = -1
        designated_cache = None
        for v in path[1:]:
            if self.view.has_cache(v):
                if self.betw[v] >= max_betw:
                    max_betw = self.betw[v]
                    designated_cache = v
        # Forward content
        for u, v in path_links(path):
            self.controller.forward_content_hop(u, v)
            if v == designated_cache:
                self.controller.put_content(v)
        self.controller.end_session()


@register_strategy('RAND_BERNOULLI_PKT_LEVEL')
class RandomBernoulliPacketLevel(Strategy):
    """Bernoulli random cache insertion.

    In this strategy, a content is randomly inserted in a cache on the path
    from serving node to receiver with probability *p*.
    """

    @inheritdoc(Strategy)
    def __init__(self, view, controller, p=0.2, **kwargs):
        super(RandomBernoulliPacketLevel, self).__init__(view, controller)
        self.p = p
    
    @inheritdoc(Strategy)
    def process_event(self, time, receiver, content, node, flow, pkt_type, log):
        # get all required data
        # Route requests to original source and queries caches on the path
        if pkt_type == 'Request':
            if node == receiver:
                self.controller.start_flow_session(time, receiver, content, flow, log)
            source = self.view.content_source(content)
            if node == source:
                path = self.view.shortest_path(node, receiver)
                link_delay = self.view.link_delay(node, path[1])
                t_event = time + link_delay
                self.controller.forward_request_hop_flow(node, path[1], flow, log)
                self.controller.add_event({'t_event': t_event, 'receiver': receiver, 'content': content, 'node': path[1], 'flow': flow, 'pkt_type': 'Data', 'log': log} )
                return
            if self.view.has_cache(node):
                self.controller.query_content_flow(node, content, flow, log)
            if (self.view.has_cache(node) and self.view.get_node_read_queue_index(node) < self.view.get_read_queue_size_limit()):
                if self.controller.get_content_flow(node, content, flow, log):
                    self.controller.push_node_read_queue(node, flow)
                    idx = self.view.get_node_read_queue_index(node)
                    t_event = time + idx * self.view.get_single_cache_read_penalty()
                    self.controller.add_event({'t_event': t_event, 'receiver': receiver, 'content': content, 'node': node, 'flow': flow, 'pkt_type': 'ReadComplete', 'log': log})
                    return

            # no cache get, forward request to the next node
            path = self.view.shortest_path(node, source)
            delay = self.view.link_delay(node, path[1])
            t_event = time + delay
            self.controller.forward_request_hop_flow(node, path[1], flow, log)
            self.controller.add_event({'t_event': t_event, 'receiver': receiver, 'content': content, 'node': path[1], 'flow': flow, 'pkt_type': 'Request', 'log': log} )
    
        elif pkt_type == 'Data':
            if node == receiver:
                self.controller.end_flow_session(flow, log)
            else:
                # no matter written or not, pass it down to the receiver
                path = self.view.shortest_path(node, receiver)
                self.controller.forward_content_hop_flow(node, path[1], flow, log)
                delay = self.view.link_delay(node, path[1])
                t_event = time + delay
                self.controller.add_event({'t_event': t_event, 'receiver': receiver, 'content': content, 'node': path[1], 'flow': flow, 'pkt_type': 'Data', 'log': log})

        elif pkt_type == 'ReadComplete':
            # cache read complete, send the content back to the receiver
            self.controller.pop_node_read_queue(node, flow)
            path = self.view.shortest_path(node, receiver)
            link_delay = self.view.link_delay(node, path[1])
            t_event = time + link_delay
            self.controller.forward_request_hop_flow(node, path[1], flow, log)
            self.controller.add_event({'t_event': t_event, 'receiver': receiver, 'content': content, 'node': path[1], 'flow': flow, 'pkt_type': 'Data', 'log': log} )
            
            # select random_cache and write the content
            for u, v in path_links(path):
            # self.controller.forward_content_hop(u, v)
                if v != receiver and self.view.has_cache(v):
                    if random.random() < self.p:
                        # current node write is not full, write the content
                        if self.view.get_node_write_queue_index(node) < self.view.get_write_queue_size_limit():
                            self.controller.push_node_write_queue(v, flow)
                            idx = self.view.get_node_write_queue_index(v)
                            t_event = time + idx * self.view.get_single_cache_write_penalty()
                            self.controller.add_event({'t_event': t_event, 'receiver': receiver, 'content': content, 'node': v, 'flow': flow, 'pkt_type': 'WriteComplete', 'log': log})

        elif pkt_type == 'WriteComplete':
            self.controller.pop_node_write_queue(node, flow)
            self.controller.put_content_flow(node, content, flow)

        else:
            raise ValueError('Invalid packet type')


@register_strategy('RAND_BERNOULLI')
class RandomBernoulli(Strategy):
    """Bernoulli random cache insertion.

    In this strategy, a content is randomly inserted in a cache on the path
    from serving node to receiver with probability *p*.
    """

    @inheritdoc(Strategy)
    def __init__(self, view, controller, p=0.2, **kwargs):
        super(RandomBernoulli, self).__init__(view, controller)
        self.p = p

    @inheritdoc(Strategy)
    def process_event(self, time, receiver, content, log):
        # get all required data
        source = self.view.content_source(content)
        path = self.view.shortest_path(receiver, source)
        # Route requests to original source and queries caches on the path
        self.controller.start_session(time, receiver, content, log)
        for u, v in path_links(path):
            self.controller.forward_request_hop(u, v)
            if self.view.has_cache(v):
                if self.controller.get_content(v):
                    serving_node = v
                    break
        else:
            # No cache hits, get content from source
            self.controller.get_content(v)
            serving_node = v
        # Return content
        path = list(reversed(self.view.shortest_path(receiver, serving_node)))
        for u, v in path_links(path):
            self.controller.forward_content_hop(u, v)
            if v != receiver and self.view.has_cache(v):
                if random.random() < self.p:
                    self.controller.put_content(v)
        self.controller.end_session()


@register_strategy('RAND_CHOICE_PKT_LEVEL')
class RandomChoicePacketLevel(Strategy):

    @inheritdoc(Strategy)
    def __init__(self, view, controller, **kwargs):
        super(RandomChoicePacketLevel, self).__init__(view, controller)

    @inheritdoc(Strategy)
    def process_event(self, time, receiver, content, node, flow, pkt_type, log):
        # get all required data
        # Route requests to original source and queries caches on the path
        if pkt_type == 'Request':
            if node == receiver:
                self.controller.start_flow_session(time, receiver, content, flow, log)
            source = self.view.content_source(content)
            if node == source:
                path = self.view.shortest_path(node, receiver)
                link_delay = self.view.link_delay(node, path[1])
                t_event = time + link_delay
                self.controller.forward_request_hop_flow(node, path[1], flow, log)
                self.controller.add_event({'t_event': t_event, 'receiver': receiver, 'content': content, 'node': path[1], 'flow': flow, 'pkt_type': 'Data', 'log': log} )
                return
            if self.view.has_cache(node):
                self.controller.query_content_flow(node, content, flow, log)
            if (self.view.has_cache(node) and self.view.get_node_read_queue_index(node) < self.view.get_read_queue_size_limit()):
                if self.controller.get_content_flow(node, content, flow, log):
                    self.controller.push_node_read_queue(node, flow)
                    idx = self.view.get_node_read_queue_index(node)
                    t_event = time + idx * self.view.get_single_cache_read_penalty()
                    self.controller.add_event({'t_event': t_event, 'receiver': receiver, 'content': content, 'node': node, 'flow': flow, 'pkt_type': 'ReadComplete', 'log': log})
                    return

            # no cache get, forward request to the next node
            path = self.view.shortest_path(node, source)
            delay = self.view.link_delay(node, path[1])
            t_event = time + delay
            self.controller.forward_request_hop_flow(node, path[1], flow, log)
            self.controller.add_event({'t_event': t_event, 'receiver': receiver, 'content': content, 'node': path[1], 'flow': flow, 'pkt_type': 'Request', 'log': log} )
    
        elif pkt_type == 'Data':
            if node == receiver:
                self.controller.end_flow_session(flow, log)
            else:
                # no matter written or not, pass it down to the receiver
                path = self.view.shortest_path(node, receiver)
                self.controller.forward_content_hop_flow(node, path[1], flow, log)
                delay = self.view.link_delay(node, path[1])
                t_event = time + delay
                self.controller.add_event({'t_event': t_event, 'receiver': receiver, 'content': content, 'node': path[1], 'flow': flow, 'pkt_type': 'Data', 'log': log})

        elif pkt_type == 'ReadComplete':
            # cache read complete, send the content back to the receiver
            self.controller.pop_node_read_queue(node, flow)
            path = self.view.shortest_path(node, receiver)
            link_delay = self.view.link_delay(node, path[1])
            t_event = time + link_delay
            self.controller.forward_request_hop_flow(node, path[1], flow, log)
            self.controller.add_event({'t_event': t_event, 'receiver': receiver, 'content': content, 'node': path[1], 'flow': flow, 'pkt_type': 'Data', 'log': log} )
            
            # select random_cache and write the content
            caches = [v for v in path[1:-1] if self.view.has_cache(v)]
            designated_cache = random.choice(caches) if len(caches) > 0 else None
            if designated_cache:
                # current node write is not full, write the content
                if self.view.get_node_write_queue_index(node) < self.view.get_write_queue_size_limit():
                    self.controller.push_node_write_queue(designated_cache, flow)
                    idx = self.view.get_node_write_queue_index(designated_cache)
                    t_event = time + idx * self.view.get_single_cache_write_penalty()
                    self.controller.add_event({'t_event': t_event, 'receiver': receiver, 'content': content, 'node': designated_cache, 'flow': flow, 'pkt_type': 'WriteComplete', 'log': log})

        elif pkt_type == 'WriteComplete':
            self.controller.pop_node_write_queue(node, flow)
            self.controller.put_content_flow(node, content, flow)

        else:
            raise ValueError('Invalid packet type')


@register_strategy('RAND_CHOICE')
class RandomChoice(Strategy):
    """Random choice strategy

    This strategy stores the served content exactly in one single cache on the
    path from serving node to receiver selected randomly.
    """

    @inheritdoc(Strategy)
    def __init__(self, view, controller, **kwargs):
        super(RandomChoice, self).__init__(view, controller)

    @inheritdoc(Strategy)
    def process_event(self, time, receiver, content, log):
        # get all required data
        source = self.view.content_source(content)
        path = self.view.shortest_path(receiver, source)
        # Route requests to original source and queries caches on the path
        self.controller.start_session(time, receiver, content, log)
        for u, v in path_links(path):
            self.controller.forward_request_hop(u, v)
            if self.view.has_cache(v):
                if self.controller.get_content(v):
                    serving_node = v
                    break
        else:
            # No cache hits, get content from source
            self.controller.get_content(v)
            serving_node = v
        # Return content
        path = list(reversed(self.view.shortest_path(receiver, serving_node)))
        caches = [v for v in path[1:-1] if self.view.has_cache(v)]
        designated_cache = random.choice(caches) if len(caches) > 0 else None
        for u, v in path_links(path):
            self.controller.forward_content_hop(u, v)
            if v == designated_cache:
                self.controller.put_content(v)
        self.controller.end_session()
