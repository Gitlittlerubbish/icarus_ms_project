#!usr/bin/python3
import matplotlib.pyplot as plt
import numpy as np


MEAN_CACHE_HIT_RATIO_LIST = []
MEAN_LATENCY_LIST = []
READ_QUEUE_SIZE_LIMITS = [3, 4, 5, 8, 10]
tick = [0, 0.01, 0.03, 0.05, 0.07, 0.09, 0.10, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.5, 0.6]
base = len(tick)
MARKERS=['1', '2', 'o','v','*','+','x','D']

def main():
    current_line_ptr = True
    with open("results.txt", "r") as result_file:
        for line in result_file:
            if "MEAN" in line:
                if current_line_ptr == True:
                    MEAN_CACHE_HIT_RATIO_LIST.append(float(line.split(": ")[1].strip()))
                    current_line_ptr = False
                    continue
                elif current_line_ptr == False:
                    MEAN_LATENCY_LIST.append(float(line.split(": ")[1].strip()))
                    current_line_ptr = True
                    continue
                
    print("Latency:")
    for idx in range(len(READ_QUEUE_SIZE_LIMITS)):
        print("READ_QUEUE_SIZE:", READ_QUEUE_SIZE_LIMITS[idx], MEAN_LATENCY_LIST[0 + base * idx:base * (idx + 1)])


    # # create plots
    # for idx in range(len(READ_QUEUE_SIZE_LIMITS)):
    #     plt.bar(range(len(tick)), MEAN_LATENCY_LIST[0 + base * idx:base * (idx + 1)], color = 'g', tick_label = tick)
    #     for x, y in zip(range(len(tick)), MEAN_LATENCY_LIST[0 + base * idx:base * (idx + 1)]):
    #         plt.text(x + 0.05, y, '%.2f' % y, ha='center', va='bottom')
    #     plt.xlabel('SINGLE_READ_PENALTY')
    #     plt.ylabel('MEAN_LATENCY')
    #     plt.title(f'MEAN_LATENCY vs SINGLE_READ_PENALTY(READ_QUEUE_SIZE:{READ_QUEUE_SIZE_LIMITS[idx]})')
    #     plt.savefig(f'MEAN_LATENCY vs SINGLE_READ_PENALTY(READ_QUEUE_SIZE:{READ_QUEUE_SIZE_LIMITS[idx]})')
    #     plt.show()

    # x = range(len(NETWORK_CACHE))
    # for idx in range(len(STRATEGY_LISTS)):
    #     plt.plot(NETWORK_CACHE, MEAN_CACHE_HIT_RATIO_LIST[0 + base * idx:base * (idx + 1)], marker=MARKERS[idx], label=STRATEGY_LISTS[idx])
    
    # plt.legend()
    # plt.xlabel('NETWORK_CACHE')
    # plt.ylabel('MEAN_CACHE_HIT_RATIO')
    # plt.savefig("MEAN_CACHE_HIT_RATIO vs NETWORK_CACHE.png")
    # plt.show()
    
    # mean latency
    x = range(len(tick))
    for idx in range(len(READ_QUEUE_SIZE_LIMITS)):
        plt.plot(tick, MEAN_LATENCY_LIST[0 + base * idx:base * (idx + 1)], marker=MARKERS[idx], label=READ_QUEUE_SIZE_LIMITS[idx])
    
    plt.legend()
    plt.xlabel('CACHE_READ_PENALTY')
    plt.ylabel('MEAN_LATENCY')
    plt.savefig("MEAN_LATENCY vs NETWORK_CACHE.png")
    plt.show()


if __name__ == "__main__":
    main()