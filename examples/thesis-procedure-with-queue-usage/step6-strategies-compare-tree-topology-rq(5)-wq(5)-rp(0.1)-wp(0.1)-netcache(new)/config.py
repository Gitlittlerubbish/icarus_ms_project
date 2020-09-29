"""Configuration file for running a single simple simulation."""
from multiprocessing import cpu_count
from collections import deque
import copy
from icarus.util import Tree

# GENERAL SETTINGS

# Level of logging output
# Available options: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL = 'INFO'

# If True, executes simulations in parallel using multiple processes
# to take advantage of multicore CPUs
PARALLEL_EXECUTION = False

# Number of processes used to run simulations in parallel.
# This option is ignored if PARALLEL_EXECUTION = False
N_PROCESSES = 1

# Number of times each experiment is replicated
N_REPLICATIONS = 1

# Granularity of caching.
# Currently, only OBJECT is supported
CACHING_GRANULARITY = 'OBJECT'

# Format in which results are saved.
# Result readers and writers are located in module ./icarus/results/readwrite.py
# Currently only PICKLE is supported
RESULTS_FORMAT = 'PICKLE'
 
# List of metrics to be measured in the experiments
# The implementation of data collectors are located in ./icarus/execution/collectors.py
DATA_COLLECTORS = ['CACHE_HIT_RATIO', 'LATENCY', 'QUEUE_USAGE']

# List of strategies
STRATEGIES = ['LCE_PKT_LEVEL', 'CL4M_PKT_LEVEL', 'LCD_PKT_LEVEL', 'PROB_CACHE_PKT_LEVEL', 'RAND_BERNOULLI_PKT_LEVEL', 'RAND_CHOICE_PKT_LEVEL', 'MRQC_PKT_LEVEL', 'MWQC_PKT_LEVEL']

# Total size of network cache as a fraction of content population
NETWORK_CACHE = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]

# Queue of experiments
EXPERIMENT_QUEUE = deque()

# Create experiment
default = Tree()

# Set topology
default['topology']['name'] = 'TREE'
default['topology']['k'] = 2
default['topology']['h'] = 5

# Set workload
default['workload'] = {
         'name':       'STATIONARY_PACKET_LEVEL',
         'n_contents': 10 ** 4,
         'n_warmup':   4 * 10 ** 5,
         'n_measured': 4 * 10 ** 5,
         'alpha':      1.0,
         'rate':       100
                       }

# Set cache placement
default['cache_placement']['name'] = 'UNIFORM'

# Set content placement
default['content_placement']['name'] = 'UNIFORM'

# Set cache replacement policy
default['cache_policy']['name'] = 'LRU'

# Set network configuration for NetworkModel
default['netconf']['read_queue_size_limit'] = 5
default['netconf']['write_queue_size_limit'] = 5
default['netconf']['single_cache_read_penalty'] = 0.10
default['netconf']['single_cache_write_penalty'] = 0.10
# Description of the experiment
# default['desc'] = "Line topology with 10 nodes"

# Append experiment to queue
for strategy in STRATEGIES:
    for network_cache in NETWORK_CACHE:
        experiment = copy.deepcopy(default)
        experiment['strategy']['name'] = strategy
        experiment['cache_placement']['network_cache'] = network_cache
        experiment['desc'] = f'''Binary-tree topology with:
                                    \t\t\t\t\t\t\t\tstrategy:{strategy}
                                    \t\t\t\t\t\t\t\theight:{experiment['topology']['h']}
                                    \t\t\t\t\t\t\t\tnetwork_cache:{experiment['cache_placement']['network_cache']}
                                    \t\t\t\t\t\t\t\tsingle_cache_read_penalty:{experiment['netconf']['single_cache_read_penalty']}
                                    \t\t\t\t\t\t\t\tread_queue_size_limit:{experiment['netconf']['read_queue_size_limit']}
                                    \t\t\t\t\t\t\t\tsignle_cache_write_penalty:{experiment['netconf']['single_cache_write_penalty']}
                                    \t\t\t\t\t\t\t\twrite_queue_size_limit:{experiment['netconf']['write_queue_size_limit']}'''
        EXPERIMENT_QUEUE.append(experiment)
