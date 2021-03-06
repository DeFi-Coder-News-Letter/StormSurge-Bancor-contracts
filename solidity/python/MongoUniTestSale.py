import sys
import pymongo
import InputGenerator
import FormulaSolidityPort
import FormulaNativePython


USERNAME = ''
PASSWORD = ''
SERVER_NAME = '127.0.0.1:27017'
DATABASE_NAME = 'test'

MINIMUM_VALUE_SUPPLY = 100
MAXIMUM_VALUE_SUPPLY = 10 ** 34
SAMPLES_COUNT_SUPPLY = 150

MINIMUM_VALUE_BALANCE = 100
MAXIMUM_VALUE_BALANCE = 10 ** 34
SAMPLES_COUNT_BALANCE = 150

MINIMUM_VALUE_RATIO = 100000
MAXIMUM_VALUE_RATIO = 900000
SAMPLES_COUNT_RATIO = 10

MINIMUM_VALUE_AMOUNT = 1
MAXIMUM_VALUE_AMOUNT = 10 ** 34
SAMPLES_COUNT_AMOUNT = 150

TRANSACTION_SUCCESS = 0
TRANSACTION_FAILURE = 1
TRANSACTION_INVALID = 2
IMPLEMENTATION_ERROR = 3


def Main():
    username = USERNAME
    password = PASSWORD
    server_name = SERVER_NAME
    database_name = DATABASE_NAME
    for arg in sys.argv[1:]:
        username = arg[len('username='):] if arg.startswith('username=') else username
        password = arg[len('password='):] if arg.startswith('password=') else password
        server_name = arg[len('server_name='):] if arg.startswith('server_name=') else server_name
        database_name = arg[len('database_name='):] if arg.startswith('database_name=') else database_name
    if username and password:
        uri = 'mongodb://{}:{}@{}/{}'.format(username, password, server_name, database_name)
    else:
        uri = 'mongodb://{}/{}'.format(server_name, database_name)
    TestAll(pymongo.MongoClient(uri)[database_name]['sale'])


def TestAll(collection):
    collection.ensure_index([(key, pymongo.ASCENDING) for key in ['supply', 'balance', 'ratio', 'amount']])
    rangeSupply = InputGenerator.UniformDistribution(MINIMUM_VALUE_SUPPLY, MAXIMUM_VALUE_SUPPLY, SAMPLES_COUNT_SUPPLY)
    rangeBalance = InputGenerator.UniformDistribution(MINIMUM_VALUE_BALANCE, MAXIMUM_VALUE_BALANCE, SAMPLES_COUNT_BALANCE)
    rangeRatio = InputGenerator.UniformDistribution(MINIMUM_VALUE_RATIO, MAXIMUM_VALUE_RATIO, SAMPLES_COUNT_RATIO)
    rangeAmount = InputGenerator.UniformDistribution(MINIMUM_VALUE_AMOUNT, MAXIMUM_VALUE_AMOUNT, SAMPLES_COUNT_AMOUNT)

    for supply in rangeSupply:
        for balance in rangeBalance:
            for ratio in rangeRatio:
                for amount in rangeAmount:
                    if amount <= supply:
                        resultSolidityPort = Run(FormulaSolidityPort, supply, balance, ratio, amount)
                        resultNativePython = Run(FormulaNativePython, supply, balance, ratio, amount)
                        if resultNativePython < 0:
                            status = TRANSACTION_INVALID
                            loss = {'absolute': 0, 'relative': 0}
                        elif resultSolidityPort < 0:
                            status = TRANSACTION_FAILURE
                            loss = {'absolute': 0, 'relative': 0}
                        elif resultNativePython < resultSolidityPort:
                            status = IMPLEMENTATION_ERROR
                            loss = {'absolute': 0, 'relative': 0}
                        else: # 0 <= resultSolidityPort <= resultNativePython
                            status = TRANSACTION_SUCCESS
                            loss = {'absolute': float(resultNativePython - resultSolidityPort), 'relative': 1 - float(resultSolidityPort / resultNativePython)}
                        filter = {
                            'supply': '{}'.format(supply),
                            'balance': '{}'.format(balance),
                            'ratio': '{}'.format(ratio),
                            'amount': '{}'.format(amount),
                        }
                        update = {
                            'resultSolidityPort': '{}'.format(resultSolidityPort),
                            'resultNativePython': '{:.2f}'.format(resultNativePython),
                            'status': status,
                            'loss': loss,
                        }
                        document = collection.find_one_and_update(filter, {'$set': update}, upsert=True, return_document=pymongo.ReturnDocument.AFTER)
                        print(', '.join('{}: {}'.format(field, document[field]) for field in ['supply', 'balance', 'ratio', 'amount', 'resultSolidityPort', 'resultNativePython', 'status', 'loss']))


def Run(module, supply, balance, ratio, amount):
    try:
        return module.calculateSaleReturn(supply, balance, ratio, amount)
    except:
        return -1


Main()
