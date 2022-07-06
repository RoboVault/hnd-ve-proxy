import pytest
from brownie import config, accounts, Contract
from _useful_methods import REL_APPROX, HND_DUST

def fund_user(user_x, usdc_whale, husdc, usdc, amount):
    usdc.approve(husdc, amount, {'from': user_x})
    husdc.mint(amount, {'from': user_x})
    assert husdc.balanceOf(user_x) > 0


def test_two_equal_deposits(chain, multistrat_proxy, husdc_gauge, gov, husdc, hnd, user, user2, usdc_amount, usdc, usdc_whale):
    # Approve strat
    multistrat_proxy.approveStrategy(husdc_gauge, user, {"from":gov})
    multistrat_proxy.approveStrategy(husdc_gauge, user2, {"from":gov})
    
    fund_user(user, usdc_whale, husdc, usdc, usdc_amount)
    fund_user(user2, usdc_whale, husdc, usdc, usdc_amount)
    
    # Deposit into multistrat proxy
    user1_amount = husdc.balanceOf(user)
    husdc.approve(multistrat_proxy, user1_amount, {'from': user})
    multistrat_proxy.deposit(husdc_gauge, user1_amount, {'from': user})
    assert multistrat_proxy.balanceOf(husdc_gauge, user) == user1_amount
    
    # Deposit into multistrat proxy
    user2_amount = husdc.balanceOf(user2)
    husdc.approve(multistrat_proxy, user2_amount, {'from': user2})
    multistrat_proxy.deposit(husdc_gauge, user2_amount, {'from': user2})
    assert multistrat_proxy.balanceOf(husdc_gauge, user2) == user2_amount
    
    # Sleep to accumulate hnd
    chain.sleep(3600 * 24)
    chain.mine()
    
    # harvest and confirm rewards are sent
    hnd_user1_balance_before = hnd.balanceOf(user)
    hnd_user2_balance_before = hnd.balanceOf(user2)
    multistrat_proxy.harvest(husdc_gauge, {'from':user})
    hnd_balance_after = hnd.balanceOf(user)
    hnd_user1_balance_after = hnd.balanceOf(user)
    hnd_user2_balance_after = hnd.balanceOf(user2)
    print('HND Balance before {0} {1}'.format(hnd_user1_balance_before, hnd_user2_balance_before))
    print('HND Balance after {0} {1}'.format(hnd_user1_balance_after, hnd_user2_balance_after))
    assert hnd_user1_balance_before < hnd_user1_balance_after
    assert hnd_user2_balance_before < hnd_user2_balance_after
    

def test_two_non_equal_deposits(chain, multistrat_proxy, husdc_gauge, gov, husdc, hnd, user, user2, usdc_amount, usdc, usdc_whale):
    # Approve strat
    multistrat_proxy.approveStrategy(husdc_gauge, user, {"from":gov})
    multistrat_proxy.approveStrategy(husdc_gauge, user2, {"from":gov})
    
    fund_user(user, usdc_whale, husdc, usdc, usdc_amount)
    fund_user(user2, usdc_whale, husdc, usdc, usdc_amount/2)
    
    # Deposit into multistrat proxy
    user1_amount = husdc.balanceOf(user)
    husdc.approve(multistrat_proxy, user1_amount, {'from': user})
    multistrat_proxy.deposit(husdc_gauge, user1_amount, {'from': user})
    assert multistrat_proxy.balanceOf(husdc_gauge, user) == user1_amount
    
    # Deposit into multistrat proxy
    user2_amount = husdc.balanceOf(user2)
    husdc.approve(multistrat_proxy, user2_amount, {'from': user2})
    multistrat_proxy.deposit(husdc_gauge, user2_amount, {'from': user2})
    assert multistrat_proxy.balanceOf(husdc_gauge, user2) == user2_amount
    
    # Sleep to accumulate hnd
    chain.sleep(3600 * 24)
    chain.mine()
    
    # harvest and confirm rewards are sent
    hnd_user1_balance_before = hnd.balanceOf(user)
    hnd_user2_balance_before = hnd.balanceOf(user2)
    multistrat_proxy.harvest(husdc_gauge, {'from':user})
    hnd_user1_balance_after = hnd.balanceOf(user)
    hnd_user2_balance_after = hnd.balanceOf(user2)
    print('HND Balance before {0} {1}'.format(hnd_user1_balance_before, hnd_user2_balance_before))
    print('HND Balance after {0} {1}'.format(hnd_user1_balance_after, hnd_user2_balance_after))
    assert hnd_user1_balance_before < hnd_user1_balance_after
    assert hnd_user2_balance_before < hnd_user2_balance_after
    assert pytest.approx(hnd_user2_balance_after * 2, rel=1e-4) == hnd_user1_balance_after


    