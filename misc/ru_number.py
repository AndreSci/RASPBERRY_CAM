
def num_to_rus(numbers: list):

    ru_number = list()

    for num in numbers:
        if num[0] == '0':
            num = 'О' + num[1:]
        elif num[0].isdigit():
            print('не число 1')
            continue

        print(f"test 3 числа: {num[1:4]}")
        if not num[1:3].isdigit():
            print('не число 2')
            continue

        print(f"test 2 буквы: {num[4:6]}")
        if num[4].isdigit() or num[5].isdigit():
            print('не буквы 2')
            continue

        ru_number.append(num.upper())

    return ru_number


if __name__ == '__main__':

    print(num_to_rus(['e100kk777', '0111pp999', '123pp555', 'в100FА777', 'f150AA777']))