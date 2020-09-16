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
                
    # print(MEAN_CACHE_HIT_RATIO_LIST)
    print("Latency:", MEAN_LATENCY_LIST)


    # create plot
    tick = [0, 0.01, 0.05, 0.08, 0.09, 0.1, 0.11, 0.12, 0.13, 0.15, 0.16, 0.17, 0.18, 0.19, 0.20, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 1, 2, 3]
    plt.bar(range(len(MEAN_CACHE_HIT_RATIO_LIST)), MEAN_CACHE_HIT_RATIO_LIST, color = 'b', tick_label = tick)
    for x, y in zip(range(len(tick)), MEAN_CACHE_HIT_RATIO_LIST):
            plt.text(x + 0.05, y, '%.2f' % y, ha='center', va='bottom')
    plt.xlabel('WRITE_PENALTY')
    plt.ylabel('MEAN_CACHE_HIT_RATIO')
    plt.title('MEAN_CACHE_HIT_RATIO vs WRITE_PENALTY')
    plt.savefig("MEAN_CACHE_HIT_RATIO vs WRITE_PENALTY.png")
    plt.show()

    plt.bar(range(len(MEAN_LATENCY_LIST)), MEAN_LATENCY_LIST, color = 'g', tick_label = tick)
    for x, y in zip(range(len(tick)), MEAN_LATENCY_LIST):
            plt.text(x + 0.05, y, '%.2f' % y, ha='center', va='bottom')
    plt.xlabel('READ_PENALTY')
    plt.ylabel('MEAN_LATENCY')
    plt.title('MEAN_LATENCY vs READ_PENALTY')
    plt.savefig('MEAN_LATENCY vs READ_PENALTY.png')
    plt.show()


if __name__ == "__main__":
    main()