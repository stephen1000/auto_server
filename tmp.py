from retry import retry
from random import randint

@retry(tries=10,delay=3)
def main():
    if randint(0,10) < 7:
        print('boo')
        raise Exception
    print('woo')

if __name__ == '__main__':
    main()