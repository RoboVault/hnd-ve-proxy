import pytest
from brownie import interface
from brownie import reverts

@pytest.fixture
def user2(accounts):
    yield accounts[7]

# TODO i'm not sure that some transaction should revert, @smoothbot?
def test_transfer_not_supported(vault, strategy, usdc, usdc_amount, user, user2):
    user1 = user
    user_balance_before = usdc.balanceOf(user1)
    usdc.approve(vault.address, usdc_amount, {"from": user1})
    vault.deposit(usdc_amount, {"from": user1})

    assert usdc.balanceOf(user1) == user_balance_before - usdc_amount 
    assert vault.totalSupply() ==  usdc_amount

    with reverts():
        vault.transfer(user2, vault.balanceOf(user1), {'from': user1})
    
    vault.approve(user2, vault.balanceOf(user1), {'from': user1})
    with reverts():
        vault.transferFrom(user1, user2, vault.balanceOf(user1), {'from':user2})

    with reverts(): 
        vault.withdraw(usdc_amount, {"from": user2})

    vault.withdraw(usdc_amount, {"from": user1})

    assert usdc.balanceOf(user1) == user_balance_before

    with reverts(): 
        vault.withdraw(usdc_amount, {"from": user1})