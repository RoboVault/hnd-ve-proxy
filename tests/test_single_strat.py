from brownie import Contract
import pytest
from _useful_methods import REL_APPROX, HND_DUST

    
def test_operation(chain, multistrat_proxy, husdc_gauge, gov, husdc, hnd, user, usdc_amount, usdc):
    # Approve strat
    multistrat_proxy.approveStrategy(husdc_gauge, user, {"from":gov})
    # Deposit `amount` of usdc into the multi proxy
    print("User amt:", usdc.balanceOf(user))
    print("User amt after deposit:", usdc.balanceOf(user))
    # mint husdc
    amount = usdc.balanceOf(user)
    usdc.approve(husdc, amount, {'from': user})
    husdc.mint(amount, {'from': user})
    assert husdc.balanceOf(user) > 0
    
    # deposit into multistrat proxy
    husdc_amount = husdc.balanceOf(user)
    husdc.approve(multistrat_proxy, husdc_amount, {'from': user})
    multistrat_proxy.deposit(husdc_gauge, husdc_amount, {'from': user})
    assert multistrat_proxy.balanceOf(husdc_gauge, user) == husdc_amount
    
    # Sleep to accumulate hnd
    chain.sleep(3600 * 24)
    chain.mine()
    
    # harvest and confirm rewards are sent
    hnd_balance_before = hnd.balanceOf(user)
    multistrat_proxy.harvest(husdc_gauge)
    hnd_balance_after = hnd.balanceOf(user)
    print('HND Balance before {}'.format(hnd_balance_before))
    print('HND Balance after {}'.format(hnd_balance_after))
    assert hnd_balance_after > hnd_balance_before

    # withdraw from gauge
    multistrat_proxy.withdraw(husdc_gauge, husdc_amount, {'from': user})
    assert husdc_amount >= husdc.balanceOf(user)
    husdc.redeem(husdc.balanceOf(user), {'from': user})
    assert usdc.balanceOf(user) >= amount
    

def test_operation_all(chain, multistrat_proxy, husdc_gauge, gov, husdc, hnd, user, usdc_amount, usdc):
    # Approve strat
    multistrat_proxy.approveStrategy(husdc_gauge, user, {"from":gov})
    # Deposit `amount` of usdc into the multi proxy
    print("User amt:", usdc.balanceOf(user))
    print("User amt after deposit:", usdc.balanceOf(user))
    # mint husdc
    amount = usdc.balanceOf(user)
    usdc.approve(husdc, amount, {'from': user})
    husdc.mint(amount, {'from': user})
    assert husdc.balanceOf(user) > 0
    
    # deposit into multistrat proxy
    husdc_amount = husdc.balanceOf(user)
    husdc.approve(multistrat_proxy, husdc_amount, {'from': user})
    multistrat_proxy.deposit(husdc_gauge, husdc_amount, {'from': user})
    assert multistrat_proxy.balanceOf(husdc_gauge, user) == husdc_amount
    
    # Sleep to accumulate hnd
    chain.sleep(3600 * 24)
    chain.mine()
    
    # harvest and confirm rewards are sent
    hnd_balance_before = hnd.balanceOf(user)
    multistrat_proxy.harvest(husdc_gauge)
    hnd_balance_after = hnd.balanceOf(user)
    print('HND Balance before {}'.format(hnd_balance_before))
    print('HND Balance after {}'.format(hnd_balance_after))
    assert hnd_balance_after > hnd_balance_before

    # withdraw from gauge
    multistrat_proxy.withdrawAll(husdc_gauge, {'from': user})
    assert husdc_amount >= husdc.balanceOf(user)
    husdc.redeem(husdc.balanceOf(user), {'from': user})
    assert usdc.balanceOf(user) >= amount