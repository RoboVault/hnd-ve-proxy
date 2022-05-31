from brownie import Contract
import pytest
from _useful_methods import REL_APPROX, HND_DUST
def approve_strategies(mock_strategy_1, mock_strategy_2, multistrat_proxy, husdc_gauge, gov, husdc):
    multistrat_proxy.approveStrategy(husdc_gauge, mock_strategy_1.address, {"from":gov})
    multistrat_proxy.approveStrategy(husdc_gauge, mock_strategy_2.address, {"from":gov})
    husdc.approve(multistrat_proxy.address, husdc.balanceOf(mock_strategy_1.address), {"from":mock_strategy_1})
    husdc.approve(multistrat_proxy.address, husdc.balanceOf(mock_strategy_2.address), {"from":mock_strategy_2})
    
def test_delayed_deposits(chain, mock_strategy_1, mock_strategy_2, husdc_amount, multistrat_proxy, husdc_gauge, gov, husdc, hnd):
    # Deposit `amount` of usdc into the multi proxy
    approve_strategies(mock_strategy_1, mock_strategy_2, multistrat_proxy, husdc_gauge, gov, husdc)

    multistrat_proxy.deposit(husdc_gauge, husdc_amount, {"from": mock_strategy_1})
    
    chain.sleep(3600 * 24)
    chain.mine() # sleeps for 1 day
    assert 1 == 0
    multistrat_proxy.deposit(husdc_gauge, husdc_amount, {"from": mock_strategy_2})
    
    # Check that the proxy have some hnd from rewards
    balance = hnd.balanceOf(multistrat_proxy.proxy())
    
    # Check that almost all the HND went to strat 1
    assert pytest.approx(hnd.balanceOf(mock_strategy_2), rel=REL_APPROX) == 0
    assert hnd.balanceOf(mock_strategy_1) > HND_DUST
    print(hnd.balanceOf(mock_strategy_1))
    


