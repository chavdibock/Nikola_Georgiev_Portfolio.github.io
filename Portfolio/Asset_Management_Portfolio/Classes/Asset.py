from abc import ABC, abstractmethod


class Asset(ABC):
    def __init__(self, symbol, name):
        self._symbol = symbol
        self._name = name

    def get_symbol(self):
        return self._symbol

    def set_symbol(self, symbol):
        if symbol is not None:
            self._symbol = symbol
        else:
            raise ValueError("Symbol cannot be None")

    def get_name(self):
        return self._name

    def set_name(self, name):
        if name is not None:
            self._name = name
        else:
            raise ValueError("Name cannot be None")

    @abstractmethod
    def assess_risk(self):
        raise NotImplementedError("NO implementation")

    def __eq__(self, other):
        if isinstance(other, Asset):
            return self.assess_risk() == other.assess_risk()




if __name__ == '__main__':
    print("Hello")
