#!usr/bin/python3
import matplotlib.pyplot as plt
import numpy as np


MEAN_RQ_USAGE_LIST = []
CACHE_READ_PENALTIES = [0.03, 0.05, 0.06, 0.08, 0.1, 0.12, 0.14, 0.16, 0.18, 0.2, 0.24, 0.26 ,0.28, 0.29, 0.3, 0.31, 0.32, 0.35, 0.36, 0.38, 0.4, 0.5, 0.6, 0.7, 0.8]
tick = [0.03, 0.05, 0.06, 0.08, 0.1, 0.12, 0.14, 0.16, 0.18, 0.2, 0.24, 0.26 ,0.28, 0.29, 0.3, 0.32, 0.35, 0.38, 0.4, 0.5, 0.6, 0.7, 0.8, 1, 1.2, 1.5]
base = len(tick)

def main():
    current_line_ptr = True
    with open("results.txt", "r") as result_file:
        for line in result_file:
            if "MEAN_RQ_USAGE:" in line:
                MEAN_RQ_USAGE_LIST.append(float(line.split(": ")[1].strip()))
                
    print("Latency:")
    print("MEAN_RQ_USAGE_LIST:", MEAN_RQ_USAGE_LIST)


    # create plots
    plt.bar(range(len(tick)), MEAN_RQ_USAGE_LIST, tick_label=tick)
    for x, y in zip(range(len(tick)), MEAN_RQ_USAGE_LIST):
        plt.text(x + 0.05, y, '%.2f' % y, ha='center', va='bottom')
    plt.xlabel('CACHE_READ_PENALTY')
    plt.ylabel('READ_QUEUE_USAGE')
    plt.title(f'READ_QUEUE_USAGE vs CACHE_READ_PENALTY')
    plt.savefig(f'CACHE_READ_PENALTY vs READ_QUEUE_USAGE)')
    plt.show()


if __name__ == "__main__":
    main()