import brownie
from brownie import Contract
import pytest
from _useful_methods import REL_APPROX, HND_DUST
    
    
def test_permissions(chain, multistrat_proxy, husdc_gauge, gov, husdc, hnd, user, usdc_amount, usdc):
    
    # Approve strat
    with brownie.reverts('!governance'):
        multistrat_proxy.approveStrategy(husdc_gauge, user, {"from":user})
    multistrat_proxy.approveStrategy(husdc_gauge, user, {"from":gov})

    # Pause strat
    with brownie.reverts('!governance'):
        multistrat_proxy.pauseStrategy(husdc_gauge, user, {"from":user})
    multistrat_proxy.pauseStrategy(husdc_gauge, user, {"from":gov})

    # Unpause strat
    with brownie.reverts('!governance'):
        multistrat_proxy.unpauseStrategy(husdc_gauge, user, {"from":user})
    multistrat_proxy.unpauseStrategy(husdc_gauge, user, {"from":gov})

    # Revoke strat
    with brownie.reverts('!governance'):
        multistrat_proxy.revokeStrategy(husdc_gauge, user, False, {"from":user})
    multistrat_proxy.revokeStrategy(husdc_gauge, user, False, {"from":gov})


def test_transfer_gov(multistrat_proxy, gov, user):

    multistrat_proxy.setGovernance(user, {'from':gov})
    assert multistrat_proxy.pendingGovernance() == user
    multistrat_proxy.acceptGovernance({'from': user})
    assert multistrat_proxy.governance() == user
    
    
def test_configs(multistrat_proxy, gov, user):
    
    # Dust
    with brownie.reverts('!governance'):
        multistrat_proxy.setDust(1e18, {"from":user})
    multistrat_proxy.setDust(1e18, {"from":gov})
    assert multistrat_proxy.dust() == 1e18
    
    # Fee
    with brownie.reverts('!governance'):
        multistrat_proxy.setFee(1000, {"from":user})
    with brownie.reverts('!fee_too_high'):
        multistrat_proxy.setFee(5001, {"from":gov})
    multistrat_proxy.setFee(5000, {"from":gov})
    assert multistrat_proxy.fee() == 5000
    
    # Rewards
    with brownie.reverts('!governance'):
        multistrat_proxy.setRewards(user, {"from":user})
    multistrat_proxy.setRewards(user, {"from":gov})
    assert multistrat_proxy.rewards() == user
    
    # Rewards
    with brownie.reverts('!governance'):
        multistrat_proxy.setfeeDistribution(user, {"from":user})
    multistrat_proxy.setfeeDistribution(user, {"from":gov})
    assert multistrat_proxy.feeDistribution() == user
    
    
def test_lock(multistrat_proxy, proxy, gov, user, hnd, hnd_whale):
    hnd.transfer(proxy, 1e18, {'from': hnd_whale})
    
    ## todo - add this test proxy to the whitelist
    # multistrat_proxy.lock({'from': gov}) 
    
    
