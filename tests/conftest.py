import pytest
from brownie import config, accounts, Contract


# TODO tests
# - FIX first test
# - Test two strats together, profit 50/50
# - Test two strats together, one with 100% allocation, one with 50% allocation, profit 67/33
# - Test one strat usdc, one frax delayed
# - Test one strat usdc, one frax together, profit % based on apr
#       - How to pull apr?
# - Test deposit, withdraw more than deposited (should fail), withdraw half (should succeed), withdraw all
# - Same test deposit, but with usdc and frax
# - Test strat deposit from not approved strat (should fail)
# - Test strat deposit from paused strat (should fail)
# - 


# THINGS I NOTICED / CHANGED
# - Multistrat deposit requires the strategy to be paused?
#       Changed from
#           require (strategies[_gauge][idx].isPaused, "!paused"); 
#       to
#           require (!strategies[_gauge][idx].isPaused, "!paused"); 
# - Anyone can call harvest(). Is this intended?
# - Anyone can call withdraw and withdrawAll() and drain the contract
#       TODO add checks
# - Do we want to let a "Paused" strategy withdraw funds? In my opinion yes
# - Withdraw: instead of sending it to msg.sender, we should send it to the correct strat
# - withdrawAll() should call withdraw for each strat, otherwise strats could "steal" other strats funds
# - If a strategy is paused, will it still receive the rewards?
# - Do we need an emergencyExit function?
# - sweepProxy could be used to steal everything if the gov address is compromized

# @pytest.fixture
# def veHNDVoter(pm, gov, veHNDVoter):
#     Vault = pm(config["dependencies"][0]).Vault
#     vault = guardian.deploy(Vault)
#     vault.initialize(token, gov, rewards, "", "", guardian, management)
#     vault.setDepositLimit(2 ** 256 - 1, {"from": gov})
#     vault.setManagement(management, {"from": gov})
#     assert vault.token() == token.address
#     yield vault
    
    
    
#     implementation = veHNDVoter.deploy({"from": account})
    
#     # Proxy admin
#     proxy_admin = ProxyAdmin.deploy({"from": account})
    
#     # Proxy
#     box_encoded_initializer_function = encode_function_data()
#     proxy = TransparentUpgradeableProxy.deploy(
#         implementation,
#         proxy_admin,
#         box_encoded_initializer_function,
#         {"from": account, "gas_limit": 1000000},
#     )
    
@pytest.fixture
def gov(accounts):
    yield accounts[0]
    
@pytest.fixture
def rewards(accounts):
    yield accounts[1]

@pytest.fixture
def husdc_whale(accounts):
    acc = accounts.at("0xaee2ae13ebf81d38df5a9ed7013e80ea3f72e39b", force=True) # 
    yield acc

@pytest.fixture
def hfrax_whale(accounts):
    acc = accounts.at("0x46b75f2d0b91d5147412d50f69b96119f5577e1b", force=True) # 
    yield acc

@pytest.fixture
def husdc(interface):
    yield interface.IERC20Extended("0x243E33aa7f6787154a8E59d3C27a66db3F8818ee")

@pytest.fixture
def hfrax(interface):
    yield interface.IERC20Extended("0xb4300e088a3AE4e624EE5C71Bc1822F68BB5f2bc")

@pytest.fixture
def hnd(interface):
    yield interface.IERC20Extended("0x10010078a54396F62c96dF8532dc2B4847d47ED3")

@pytest.fixture
def husdc_amount(husdc):
    amount = 10_000 * 10 ** husdc.decimals()
    yield amount

@pytest.fixture
def hfrax_amount(hfrax):
    amount = 10_000 * 10 ** hfrax.decimals()
    yield amount

@pytest.fixture
def hndVoterProxy(veHNDVoter, gov):
    voter = veHNDVoter.deploy({"from": gov})
    voter.initialize(gov)
    yield voter

@pytest.fixture
def multistrat_proxy(gov, hndVoterProxy, MultiStrategyProxy):
    strategy = MultiStrategyProxy.deploy({"from": gov})
    strategy.initialize(gov, hndVoterProxy)
    hndVoterProxy.setStrategy(strategy.address, {"from": gov})
    yield strategy

@pytest.fixture
def husdc_gauge():
    yield "0x110614276F7b9Ae8586a1C1D9Bc079771e2CE8cF"

@pytest.fixture
def hfrax_gauge():
    yield "0x2c7a9d9919f042C4C120199c69e126124d09BE7c"

@pytest.fixture
def oz(pm):
    yield pm(config["dependencies"][0])

# Accounts 6-7-8 are used as "mock strategies"

@pytest.fixture
def mock_strategy_1(husdc_whale, husdc, accounts, husdc_amount):
    husdc.approve(accounts[6], husdc_amount, {"from": husdc_whale})
    husdc.transfer(accounts[6], husdc_amount, {"from": husdc_whale}) 
    yield accounts[6]

@pytest.fixture
def mock_strategy_2(husdc_whale, husdc, accounts, husdc_amount):
    husdc.approve(accounts[7], husdc_amount, {"from": husdc_whale})
    husdc.transfer(accounts[7], husdc_amount, {"from": husdc_whale})
    yield accounts[7]

@pytest.fixture
def mock_strategy_frax(hfrax_whale, hfrax, accounts, hfrax_amount):
    hfrax.approve(accounts[8], hfrax_amount, {"from": hfrax_whale})
    hfrax.transfer(accounts[8], hfrax_amount, {"from": hfrax_whale})
    yield accounts[8]
# Function scoped isolation fixture to enable xdist.
# Snapshots the chain before each test and reverts after test completion.
@pytest.fixture(scope="function", autouse=True)
def shared_setup(fn_isolation):
    pass
