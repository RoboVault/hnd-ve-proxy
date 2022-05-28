import brownie
from brownie import Contract
import random
import pytest

def approve_strategies(mock_strategy_1, mock_strategy_2, multistrat_proxy, husdc_gauge, gov):
    multistrat_proxy.approveStrategy(husdc_gauge, mock_strategy_1.address, {"from":gov})
    multistrat_proxy.approveStrategy(husdc_gauge, mock_strategy_2.address, {"from":gov})

def test_delayed_deposits(mock_strategy_1, mock_strategy_2, husdc_amount, multistrat_proxy, husdc_gauge, gov):
    # Deposit `amount` of usdc into the multi proxy
    approve_strategies(mock_strategy_1, mock_strategy_2, multistrat_proxy, husdc_gauge, gov)

    multistrat_proxy.deposit(husdc_gauge, husdc_amount, {"from": mock_strategy_1})

