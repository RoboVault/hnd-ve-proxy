from brownie import Contract
import pytest
from _useful_methods import REL_APPROX, HND_DUST
def approve_strategies(mock_strategy_1, mock_strategy_2, multistrat_proxy, husdc_gauge, gov, husdc):
    
    multistrat_proxy.approveStrategy(husdc_gauge, mock_strategy_2.address, {"from":gov})
    husdc.approve(multistrat_proxy.address, husdc.balanceOf(mock_strategy_1.address), {"from":mock_strategy_1})
    husdc.approve(multistrat_proxy.address, husdc.balanceOf(mock_strategy_2.address), {"from":mock_strategy_2})
    

def test_operation_single_strat(chain, deployed_vault, multistrat_proxy, husdc_gauge, gov, husdc, hnd, strategy, user, usdc_amount, usdc):
    # Approve strat
    multistrat_proxy.approveStrategy(husdc_gauge, strategy.address, {"from":gov})

    # Deposit `amount` of usdc into the multi proxy
    print("User amt:", usdc.balanceOf(user))
    deployed_vault.deposit(usdc_amount, {"from": user})
    print("User amt after deposit:", usdc.balanceOf(user))
    print("Vault amt after deposit:", usdc.balanceOf(deployed_vault))
    print("Balance of gauge", husdc.balanceOf(husdc_gauge))
    strategy.harvest()
    print("Balance of gauge after", husdc.balanceOf(husdc_gauge))

    chain.sleep(3600 * 24)
    chain.mine() # sleeps for 1 day
    multistrat_proxy.harvest(husdc_gauge)
    strategy.harvest()


    # All HND should be sold
    hnd_balance = hnd.balanceOf(strategy)
    
    # Want should increase, hnd should be sold
    print("EstimatedTotalAssets", strategy.estimatedTotalAssets())
    assert usdc_amount < strategy.estimatedTotalAssets()
    assert pytest.approx(hnd_balance, rel=REL_APPROX) == 0

    # Try to withdraw everything
    deployed_vault.updateStrategyDebtRatio(strategy.address, 0, {"from": gov})
    chain.sleep(1)
    strategy.harvest()
    assert strategy.estimatedTotalAssets() < 10 ** (usdc.decimals() - 3)  # near zero

    