"""Different typed of events

This module provides different events for workload, i.e., packet-level events
and data-link-level events
"""
from __future__ import division
import random
import networkx as nx
from enum import Enum, unique

from icarus.util import iround, inheritdoc
from icarus.registry import register_cache_placement
from icarus.scenarios.algorithms import compute_clusters, compute_p_median, deploy_clusters

__all__ = [
    'PacketType',
    'Event',
    'EventPacketLevel'
          ]

@unique
class PacketType(Enum):
    """Different packet types"""
    REQUEST = 0
    DATA = 1
    READ_COMPLETE = 2


class Event(object):
    """Base event imported by all other event classes"""

    def __init__(self, time, receiver, content, log, **kwargs):
        """Constructor

        Parameters
        ----------
        time : Timestamp
            The timestamp of an event
        receiver : 


        kwargs : keyworded arguments, optional
            Additional event parameters
        """
        self.time = time
        self.receiver = receiver
        self.content = content
        self.log = log


class EventPacketLevel(Event):

    @inheritdoc(Event)
    def __init__(self, time, receiver, content, log, node, flow, pkt_type):
        self.time = time
        self.receiver = receiver
        self.content = content
        self.log = log
        self.node = node
        self.flow = flow
        self.pkt_type = pkt_type





