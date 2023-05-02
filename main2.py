from os import listdir
from os.path import isfile, join
from misc.ai import AiClass
import datetime
import threading


def func_chunk(lst, n):
    """ Генератор деления списка на указанное количество частей """

    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def thr_main(thr_name: str, list_files: list):
    recon = AiClass()

    len_files = len(list_files)

    index = 1
    for it in list_files:
        start_time = datetime.datetime.now()

        recon.find_plate(it)

        end_time = datetime.datetime.now()
        delta_time = end_time - start_time

        print(f"{thr_name} - Файл {index} из {len_files} - Время обработки: {delta_time.total_seconds()} ms.")
        index += 1

def thr_recon_number(thr_name: str, frame):
    pass


def main_recon():
    thr_list = list()

    for it in range(0, thr_step):

        thr_list.append(threading.Thread(target=thr_main, args=[f'THR_{it}', list_files[it]]))

    start_time = datetime.datetime.now()

    for thr in thr_list:
        thr.start()

    for thr in thr_list:
        thr.join()

    end_time = datetime.datetime.now()
    delta_time = end_time - start_time

def main():

    only_files = [f for f in listdir('./Images/') if isfile(join('./Images/', f))]

    thr_step = 3

    sep_step = int((len(only_files) / thr_step) + 1)
    list_files = list(func_chunk(only_files, sep_step))

    # print(len(list_files[0]))
    # print(len(list_files[1]))
    # print(len(list_files[2]))
    # print(len(list_files[3]))
    print(len(list_files))

    thr_list = list()

    for it in range(0, thr_step):

        thr_list.append(threading.Thread(target=thr_main, args=[f'THR_{it}', list_files[it]]))

    start_time = datetime.datetime.now()

    for thr in thr_list:
        thr.start()

    for thr in thr_list:
        thr.join()

    end_time = datetime.datetime.now()
    delta_time = end_time - start_time

    print(f"FINISH: time - {delta_time} ms.")


if __name__ == '__main__':
    main()
