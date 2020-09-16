#!usr/bin/python3
import matplotlib.pyplot as plt
import numpy as np


MEAN_CACHE_HIT_RATIO_LIST = []
MEAN_LATENCY_LIST = []
STRATEGY_LISTS = ['LCE_PKT_LEVEL', 'CL4M_PKT_LEVEL', 'LCD_PKT_LEVEL', 'PROB_CACHE_PKT_LEVEL', 'RAND_BERNOULLI_PKT_LEVEL', 'RAND_CHOICE_PKT_LEVEL', 'MRQC_PKT_LEVEL', 'MWQC_PKT_LEVEL']
NETWORK_CACHE = [0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08]
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
            
    base = len(NETWORK_CACHE)    
    for idx in range(len(STRATEGY_LISTS)):
        print("Strategy:", STRATEGY_LISTS[idx])
        print("Cache-hit-ratio", MEAN_CACHE_HIT_RATIO_LIST[0 + base * idx:base * (idx + 1)])
        print("Latency:", MEAN_LATENCY_LIST[0 + base * idx:base * (idx + 1)])


    # # bar plot
    # tick = ['CL4M_PKT_LEVEL', 'LCD_PKT_LEVEL', 'PROB_CACHE_PKT_LEVEL', 'RAND_BERNOULLI_PKT_LEVEL', 'RAND_CHOICE_PKT_LEVEL', 'MRQC_PKT_LEVEL']
    # plt.bar(range(len(MEAN_CACHE_HIT_RATIO_LIST)), MEAN_CACHE_HIT_RATIO_LIST, color = 'b', tick_label = tick)
    # for x, y in zip(range(len(tick)), MEAN_CACHE_HIT_RATIO_LIST):
    #         plt.text(x + 0.05, y, '%.2f' % y, ha='center', va='bottom')
    # plt.xlabel('WRITE_PENALTY')
    # plt.ylabel('MEAN_CACHE_HIT_RATIO')
    # plt.title('MEAN_CACHE_HIT_RATIO vs WRITE_PENALTY')
    # plt.savefig("MEAN_CACHE_HIT_RATIO vs WRITE_PENALTY.png")
    # plt.show()

    # plt.bar(range(len(MEAN_LATENCY_LIST)), MEAN_LATENCY_LIST, color = 'g', tick_label = tick)
    # for x, y in zip(range(len(tick)), MEAN_LATENCY_LIST):
    #         plt.text(x + 0.05, y, '%.2f' % y, ha='center', va='bottom')
    # plt.xlabel('READ_PENALTY')
    # plt.ylabel('MEAN_LATENCY')
    # plt.title('MEAN_LATENCY vs READ_PENALTY')
    # plt.savefig('MEAN_LATENCY vs READ_PENALTY.png')
    # plt.show()

    # line charts
    # cache hit ratio
    x = range(len(NETWORK_CACHE))
    for idx in range(len(STRATEGY_LISTS)):
        plt.plot(NETWORK_CACHE, MEAN_CACHE_HIT_RATIO_LIST[0 + base * idx:base * (idx + 1)], marker=MARKERS[idx], label=STRATEGY_LISTS[idx])
    
    plt.legend()
    plt.xlabel('NETWORK_CACHE')
    plt.ylabel('MEAN_CACHE_HIT_RATIO')
    plt.savefig("MEAN_CACHE_HIT_RATIO vs NETWORK_CACHE.png")
    plt.show()
    
    # mean latency
    x = range(len(NETWORK_CACHE))
    for idx in range(len(STRATEGY_LISTS)):
        plt.plot(NETWORK_CACHE, MEAN_LATENCY_LIST[0 + base * idx:base * (idx + 1)], marker=MARKERS[idx], label=STRATEGY_LISTS[idx])
    
    plt.legend()
    plt.xlabel('NETWORK_CACHE')
    plt.ylabel('MEAN_LATENCY')
    plt.savefig("MEAN_LATENCY vs NETWORK_CACHE.png")
    plt.show()
    


if __name__ == "__main__":
    main()