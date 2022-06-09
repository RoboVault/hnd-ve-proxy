import pytest
from brownie import config, accounts, Contract
from _useful_methods import REL_APPROX, HND_DUST

def second_vault_usdc(pm, gov, usdc, chain, usdc_amount, usdc_whale):
    Vault = pm(config["dependencies"][1]).Vault
    vault = gov.deploy(Vault)
    vault.initialize(usdc, gov, gov, "TestVault2", "testUSDC2", gov)
    vault.setDepositLimit(2 ** 256 - 1, {"from": gov})
    vault.setManagement(gov, {"from": gov})
    usdc.approve(vault.address, usdc_amount, {"from": usdc_whale})
    # harvest
    chain.sleep(1)
    yield vault

def second_strategy_usdc(
    gov,
    LenderStrategy,
    second_vault_usdc,
    multistrat_proxy,
    husdc_gauge,
    husdc
):
    strategy = gov.deploy(LenderStrategy, second_vault_usdc, "Lender2", multistrat_proxy.address, husdc_gauge, husdc.address)
    strategy.setKeeper(gov)
    second_vault_usdc.addStrategy(strategy, 10_000, 0, 2 ** 256 - 1, 1_000, {"from": gov})
    yield strategy




@pytest.mark.skip(reason="Testing frax")
def test_two_deposits(chain, deployed_vault, multistrat_proxy, husdc_gauge, gov, husdc, hnd, strategy, user, usdc_amount, usdc, second_vault_usdc, second_strategy_usdc, usdc_whale):
    # Approve strat
    multistrat_proxy.approveStrategy(husdc_gauge, strategy.address, {"from":gov})
    multistrat_proxy.approveStrategy(husdc_gauge, second_strategy_usdc.address, {"from":gov})
    
    deployed_vault.deposit(usdc_amount, {"from": user})
    second_vault_usdc.deposit(usdc_amount, {"from": usdc_whale})

    # Deposits into multistrat
    strategy.harvest()
    second_strategy_usdc.harvest()
    # sleeps for 1 day
    chain.sleep(3600 * 24)
    chain.mine() 
    multistrat_proxy.harvest(husdc_gauge)
    # Rewards should be the same
    pytest.approx(hnd.balanceOf(strategy), rel=REL_APPROX) == hnd.balanceOf(second_strategy_usdc)
    strategy.harvest()
    second_strategy_usdc.harvest()
    pytest.approx(strategy.estimatedTotalAssets(), rel=REL_APPROX) == second_strategy_usdc.estimatedTotalAssets()
    assert strategy.estimatedTotalAssets() > usdc_amount
    assert second_strategy_usdc.estimatedTotalAssets() > usdc_amount


@pytest.mark.skip(reason="Testing frax")
def test_delayed_deposits(chain, deployed_vault, multistrat_proxy, husdc_gauge, gov, husdc, hnd, strategy, user, usdc_amount, usdc, second_vault_usdc, second_strategy_usdc, usdc_whale):
    # Approve strat
    multistrat_proxy.approveStrategy(husdc_gauge, strategy.address, {"from":gov})
    multistrat_proxy.approveStrategy(husdc_gauge, second_strategy_usdc.address, {"from":gov})
    
    deployed_vault.deposit(usdc_amount, {"from": user})
    strategy.harvest()
    # sleeps for 1 day
    chain.sleep(3600 * 24)
    chain.mine() 
    
    second_vault_usdc.deposit(usdc_amount, {"from": usdc_whale})
    second_strategy_usdc.harvest()
    multistrat_proxy.harvest(husdc_gauge)
    # Check that almost all the HND went to strat 1
    assert hnd.balanceOf(second_strategy_usdc) < HND_DUST
    assert hnd.balanceOf(second_strategy_usdc) * 100 < hnd.balanceOf(strategy)

    strategy.harvest()
    second_strategy_usdc.harvest()

    assert strategy.estimatedTotalAssets() > usdc_amount
    assert strategy.estimatedTotalAssets() > second_strategy_usdc.estimatedTotalAssets()

    # Also test withdrawAll directly from MultiStrategyProxy
    multistrat_proxy.withdrawAll(husdc_gauge, {"from": second_strategy_usdc})

    
# @pytest.fixture
# def second_vault_frax(pm, gov, frax, chain, frax_amount, frax_whale):
#     Vault = pm(config["dependencies"][1]).Vault
#     vault = gov.deploy(Vault)
#     vault.initialize(frax, gov, gov, "TestVault2", "testUSDC2", gov)
#     vault.setDepositLimit(2 ** 256 - 1, {"from": gov})
#     vault.setManagement(gov, {"from": gov})
#     frax.approve(vault.address, frax_amount, {"from": frax_whale})
#     # harvest
#     chain.sleep(1)
#     yield vault

# @pytest.fixture
# def second_strategy_frax(
#     gov,
#     LenderStrategy,
#     second_vault_frax,
#     multistrat_proxy,
#     hfrax_gauge,
#     hfrax
# ):
#     strategy = gov.deploy(LenderStrategy, second_vault_frax, "Lender2", multistrat_proxy.address, hfrax_gauge, hfrax.address)
#     strategy.setKeeper(gov)
#     second_vault_frax.addStrategy(strategy, 10_000, 0, 2 ** 256 - 1, 1_000, {"from": gov})
#     yield strategy

# def test_two_deposits_usdc_frax(chain, deployed_vault, multistrat_proxy, husdc_gauge, hfrax_gauge, gov, husdc, hnd, strategy, user, usdc_amount, usdc, second_vault_frax, second_strategy_frax, frax_whale):
#     # Approve strat
#     multistrat_proxy.approveStrategy(husdc_gauge, strategy.address, {"from":gov})
#     multistrat_proxy.approveStrategy(hfrax_gauge, second_strategy_frax.address, {"from":gov})
    
#     deployed_vault.deposit(usdc_amount, {"from": user})
#     second_vault_frax.deposit(usdc_amount, {"from": frax_whale})

#     # Deposits into multistrat
#     strategy.harvest()
#     second_strategy_frax.harvest()
#     # sleeps for 1 day
#     chain.sleep(3600 * 24)
#     chain.mine() 
#     multistrat_proxy.harvest(husdc_gauge)
#     # Rewards should be different, based on allocation

    
#     strategy.harvest()
#     second_strategy_frax.harvest()

#     assert strategy.estimatedTotalAssets() > usdc_amount
#     assert second_strategy_frax.estimatedTotalAssets() > usdc_amount