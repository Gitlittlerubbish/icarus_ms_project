#!usr/bin/python3
import matplotlib.pyplot as plt
import numpy as np


MEAN_CACHE_HIT_RATIO_LIST = []
MEAN_LATENCY_LIST = []
READ_QUEUE_SIZE_LIMITS = [3, 5, 8, 10, 15, 20, 25]
tick = [0, 0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.10]
base = len(tick)

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


    # create plots
    for idx in range(len(READ_QUEUE_SIZE_LIMITS)):
        plt.bar(range(len(tick)), MEAN_LATENCY_LIST[0 + base * idx:base * (idx + 1)], color = 'g', tick_label = tick)
        for x, y in zip(range(len(tick)), MEAN_LATENCY_LIST[0 + base * idx:base * (idx + 1)]):
            plt.text(x + 0.05, y, '%.2f' % y, ha='center', va='bottom')
        plt.xlabel('SINGLE_READ_PENALTY')
        plt.ylabel('MEAN_LATENCY')
        plt.title(f'MEAN_LATENCY vs SINGLE_READ_PENALTY(READ_QUEUE_SIZE:{READ_QUEUE_SIZE_LIMITS[idx]})')
        plt.savefig(f'MEAN_LATENCY vs SINGLE_READ_PENALTY(READ_QUEUE_SIZE:{READ_QUEUE_SIZE_LIMITS[idx]})')
        plt.show()


if __name__ == "__main__":
    main()