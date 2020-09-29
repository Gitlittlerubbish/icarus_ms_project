#!usr/bin/python3
import matplotlib.pyplot as plt
import numpy as np


MEAN_CACHE_HIT_RATIO_LIST = []
MEAN_LATENCY_LIST = []


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
                
    print("Cache-hit-ratio", MEAN_CACHE_HIT_RATIO_LIST)
    print("Latency:", MEAN_LATENCY_LIST)


    # create plot
    tick = [0, 0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.10, 0.20, 0.30, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1, 1.1, 1.2, 2, 3]
    plt.bar(range(len(MEAN_CACHE_HIT_RATIO_LIST)), MEAN_CACHE_HIT_RATIO_LIST, tick_label = tick)
    for x, y in zip(range(len(tick)), MEAN_CACHE_HIT_RATIO_LIST):
            plt.text(x + 0.05, y, '%.2f' % y, ha='center', va='bottom')
    plt.xlabel('WRITE_PENALTY (s)')
    plt.ylabel('MEAN_CACHE_HIT_RATIO')
    plt.title('MEAN_CACHE_HIT_RATIO vs WRITE_PENALTY')
    plt.savefig("MEAN_CACHE_HIT_RATIO vs WRITE_PENALTY.png")
    plt.show()

    plt.bar(range(len(MEAN_LATENCY_LIST)), MEAN_LATENCY_LIST, color = 'g', tick_label = tick)
    for x, y in zip(range(len(tick)), MEAN_LATENCY_LIST):
            plt.text(x + 0.05, y, '%.2f' % y, ha='center', va='bottom')
    plt.xlabel('WRITE_PENALTY')
    plt.ylabel('MEAN_LATENCY')
    plt.title('MEAN_LATENCY vs WRITE_PENALTY')
    plt.savefig('MEAN_LATENCY vs WRITE_PENALTY.png')
    plt.show()
    # x = range(len(tick))
    # plt.plot(tick, MEAN_CACHE_HIT_RATIO_LIST)
    
    # plt.legend()
    # plt.xlabel('CACHE_READ_PENALTY')
    # plt.ylabel('MEAN_CACHE_HIT_RATIO')
    # plt.savefig("MEAN_CACHE_HIT_RATIO vs NETWORK_CACHE.png")
    # plt.show()


if __name__ == "__main__":
    main()