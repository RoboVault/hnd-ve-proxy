import pytest
from brownie import config, accounts, Contract
from _useful_methods import REL_APPROX, HND_DUST





@pytest.fixture
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

@pytest.fixture
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



def test_two_deposits(chain, deployed_vault, multistrat_proxy, husdc_gauge, gov, husdc, hnd, strategy, user, usdc_amount, usdc, second_vault_usdc, second_strategy_usdc, usdc_whale):

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

def test_delayed_deposits(chain, deployed_vault, multistrat_proxy, husdc_gauge, gov, husdc, hnd, strategy, user, usdc_amount, usdc, second_vault_usdc, second_strategy_usdc):
    # Deposits into multistrat
    strategy.harvest()
    second_strategy_usdc.harvest()
    # sleeps for 1 day
    chain.sleep(3600 * 24)
    chain.mine() 
    multistrat_proxy.harvest(husdc)
    # Rewards should be the same

    pytest.approx(hnd.balanceOf(strategy), rel=REL_APPROX) == hnd.balanceOf(second_strategy_usdc)

    # Check that almost all the HND went to strat 1
    assert pytest.approx(hnd.balanceOf(second_strategy_usdc), rel=REL_APPROX) == 0

    strategy.harvest()
    second_strategy_usdc.harvest()
    pytest.approx(strategy.estimatedTotalAssets(), rel=REL_APPROX) == second_strategy_usdc.estimatedTotalAssets()

    assert strategy.estimatedTotalAssets() > usdc_amount
    assert strategy.estimatedTotalAssets() > second_strategy_usdc.estimatedTotalAssets()

    # Also test withdrawAll directly from MultiStrategyProxy
    multistrat_proxy.withdrawAll(husdc_gauge, {"from": second_strategy_usdc})

    



