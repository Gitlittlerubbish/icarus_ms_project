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
    
    print("Cache-hit-ratio:", MEAN_CACHE_HIT_RATIO_LIST)
    print("Latency:", MEAN_LATENCY_LIST)


    # create plot
    tick = [0, 2, 6, 8, 10, 12, 14, 16]
    plt.bar(range(len(MEAN_CACHE_HIT_RATIO_LIST)), MEAN_CACHE_HIT_RATIO_LIST, color = 'b', tick_label = tick)
    for x, y in zip(range(len(MEAN_CACHE_HIT_RATIO_LIST)), MEAN_CACHE_HIT_RATIO_LIST):
        plt.text(x+0.05, y, '%.3f' % y, ha='center', va='bottom')
    plt.xlabel('SINGLE_WRITE_PENALTY')
    plt.ylabel('MEAN_CACHE_HIT_RATIO')
    plt.title('MEAN_CACHE_HIT_RATIO vs SINGLE_WRITE_PENALTY')
    plt.savefig("MEAN_CACHE_HIT_RATIO vs SINGLE_WRITE_PENALTY.png")
    plt.show()

    plt.bar(range(len(MEAN_LATENCY_LIST)), MEAN_LATENCY_LIST, color = 'g', tick_label = tick)
    for x, y in zip(range(len(MEAN_LATENCY_LIST)), MEAN_LATENCY_LIST):
        plt.text(x+0.05, y, '%.3f' % y, ha='center', va='bottom')
    plt.xlabel('SINGLE_WRITE_PENALTY')
    plt.ylabel('MEAN_LATENCY')
    plt.title('MEAN_LATENCY vs SINGLE_WRITE_PENALTY')
    plt.savefig('MEAN_LATENCY vs SINGLE_WRITE_PENALTY.png')
    plt.show()


if __name__ == "__main__":
    main()