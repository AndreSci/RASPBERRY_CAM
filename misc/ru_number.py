from utils.consts import CLASS_ID


def num_is_rus(numbers: list):
    global CLASS_ID

    ru_number = list()

    for num in numbers:

        number = list()

        if num[0] == '0':
            number.append('О')
        elif num[0].isdigit():
            continue
        else:
            number.append(num[0])

        for n in num[1:3]:
            if not n.isdigit():
                continue

        if num[4].isdigit():
            if num[4] == '0':
                num[4] = 'О'
        if num[5].isdigit():
            continue

        ru_number.append(num.upper())

    return ru_number


if __name__ == '__main__':

    print(num_is_rus([['0', '1', '2', '3', 'p', 'p', '7', '7']]))