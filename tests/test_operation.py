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
    
    # Approve strat
    multistrat_proxy.setGovernance(user, {'from':gov})
    assert multistrat_proxy.pendingGovernance() == user
    multistrat_proxy.acceptGovernance({'from': user})
    assert multistrat_proxy.governance() == user
    
    
