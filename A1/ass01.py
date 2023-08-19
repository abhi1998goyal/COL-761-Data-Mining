import pandas as pd
from mlxtend.preprocessing import TransactionEncoder
from mlxtend.frequent_patterns import fpgrowth
from math import log
from functools import partial
import multiprocessing
import sys
import pickle
from typing import Final
import time

minisupport: Final = 0.3

# secret = "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"

sorted_pattern_to_index = {}


def log2(x: int) -> float:
    return log(x, 2)


def Unary(x):
    return (x - 1) * '0' + '1'


def Binary(x, l=1):
    s = '{0:0%db}' % l
    return s.format(x)


def Elias_Gamma(x):
    if x == 0:
        return '0'

    n = 1 + int(log2(x))
    b = x - 2 ** (int(log2(x)))

    l = int(log2(x))

    return Unary(n) + Binary(b, l)


def process_transaction(transaction_set, sorted_pattern_to_index):
    compressed_set = set()
    for item_st, cod in sorted_pattern_to_index.items():
        if item_st.issubset(transaction_set):
            transaction_set = transaction_set - item_st
            compressed_set.add(sorted_pattern_to_index.get(frozenset(item_st)))
    compressed_set.update(transaction_set)
    return compressed_set


def minsupport():
    return minisupport


def compress(inputPath, outputPath):
    global sorted_pattern_to_index
    list_of_sets = None
    te_ary = None
    start_size = None
    te = TransactionEncoder()
    try:
        df = pd.read_table(inputPath, sep="\s+", header=None)
        start_size = df.size
        print("size of data before compression =", start_size)
        te_ary = te.fit(list(df.values.tolist())).transform(df.values.tolist())
        list_of_sets = [set(row) for _, row in df.iterrows()]
        dfr = pd.DataFrame(te_ary, columns=te.columns_)
        print(dfr)
        gd = fpgrowth(dfr, min_support=minsupport(), use_colnames=True)
        print(gd)
        gd = gd[gd['itemsets'].str.len() >= 2]
        gd["frequency"] = gd["support"] * (gd['itemsets'].str.len())
        pattern_to_index = {frozenset(itemset): hex(int(Elias_Gamma(index), 2)) for index, itemset in
                            enumerate(gd['itemsets'])}
        sorted_pattern_to_index = dict(sorted(pattern_to_index.items(), key=lambda item: len(item[0]), reverse=True))
    except:
        transactions = []
        with open(inputPath, 'r') as file:
            for line in file:
                items = line.strip().split()  # Split the line into items
                transactions.append(items)
        start_size = sum([len(listElem) for listElem in transactions])
        print("size of data before compression =", start_size)
        te_ary = te.fit(transactions).transform(transactions)
        list_of_sets = [set(items) for items in transactions]
        dfr = pd.DataFrame(te_ary, columns=te.columns_)
        print(dfr)
        gd = fpgrowth(dfr, min_support=minsupport(), use_colnames=True)
        print(gd)
        gd = gd[len(gd['itemsets']) >= 2]
        gd["frequency"] = gd["support"] * len(gd['itemsets'])
        pattern_to_index = {frozenset(itemset): hex(int(Elias_Gamma(index), 2)) for index, itemset in
                            enumerate(gd['itemsets'])}
        sorted_pattern_to_index = dict(sorted(pattern_to_index.items(), key=lambda item: len(item[0]), reverse=True))
    finally:
        num_cores = multiprocessing.cpu_count()
        print("number of cores =", num_cores)
        partial_process = partial(process_transaction, sorted_pattern_to_index=sorted_pattern_to_index)
        # Create a multiprocessing pool
        pool = multiprocessing.Pool(num_cores)

        # Parallelize the processing of transaction sets
        compressed_lst = pool.map(partial_process, list_of_sets)
        pool.close()
        pool.join()
        cmp_df = pd.DataFrame(compressed_lst)
        end_size = cmp_df.size
        print("size of data after compression =", end_size)
        print("compression ratio =", end_size / start_size)
        cmp_df.to_csv(outputPath, sep='\t', index=False, header=False)
        with open('sorted_pattern_to_index.pkl', 'wb') as file:
            pickle.dump(sorted_pattern_to_index, file)


def decompress(inputPath, outputPath):
    with open('sorted_pattern_to_index.pkl', 'rb') as file:
        sorted_pattern_to_index = pickle.load(file)
    # cf = pd.read_table(inputPath, sep="\s+",header=None)
    transactions = []
    with open(inputPath, 'r') as file:
        for line in file:
            items = line.strip().split()  # Split the line into items
            transactions.append(items)

    print(sorted_pattern_to_index)
    decomp_lst = []
    rev_indx = {str(value): key for key, value in sorted_pattern_to_index.items()}
    list_of_compressed_sets = [set(items) for items in transactions]
    # list_of_compressed_sets = [set(row) for _, row in cf.iterrows()]
    for comp_set in list_of_compressed_sets:
        decomp_set = set()
        for comp_item in comp_set:
            if comp_item == 'nan':
                continue
            elif str(comp_item).startswith("0x"):
                decomp_set.update(rev_indx.get(str(comp_item), []))
            else:
                decomp_set.add(comp_item)
        decomp_lst.append(decomp_set)
    pd.DataFrame(decomp_lst).to_csv(outputPath, sep='\t', index=False, header=False)


def compress_main(input_path, output_path):
    global sorted_pattern_to_index
    sorted_pattern_to_index = compress(input_path, output_path)


def decompress_main(input_path, output_path):
    decompress(input_path, output_path)


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python ass01.py [C/D] input_path output_path")
    elif sys.argv[1] == 'C':
        """
            suggested command format: python ass01.py C datasets/originals/D_small.dat datasets/compressed/com_small.dat
        """
        print("Compression:")
        start = time.time()
        print("started at", start)
        compress_main(sys.argv[2], sys.argv[3])
        end = time.time()
        print("Ended at", end)
        print("time taken to compress =", end - start)
        print('Compression complete')
    elif sys.argv[1] == 'D':
        """
            suggested command format: python ass01.py D datasets/compressed/com_small.dat datasets/compressed/de_small.dat
        """
        decompress_main(sys.argv[2], sys.argv[3])
        print('Decompression complete')
    elif sys.argv[1] == 'E':
        print('Exiting the program')
        sys.exit(0)
