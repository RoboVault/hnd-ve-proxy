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

""" USEFUL COMMANDS (for cli)

px = multistrat_proxy.proxy()
husdc.balanceOf(strategy)
comptroller = interface.ComptrollerInterface("0x21A4961B11c940fbeF57b1EB64FD646c880377e4")

comptroller.transferAllowed(husdc.address, strategy.address, px, 100, {"from": multistrat_proxy})
husdc.transferFrom(strategy, prx, 100, {"from": multistrat_proxy})
"""

# QUESTIONS / THINGS THAT I HAVE CHANGED
# - Multistrat deposit requires the strategy to be paused?
#       Changed from
#           require (strategies[_gauge][idx].isPaused, "!paused"); 
#       to
#           require (!strategies[_gauge][idx].isPaused, "!paused"); 
# - Anyone can call harvest(). Is this intended? -> in any case, they could call harvest by depositing/withdrawing something in any strat
# - Do we need an emergencyExit function? Or a pause function for the whole MultiStrategy? (retire everything from hnd and return want to the strategist?)
# - proxy.safeExecute(hnd, 0, abi.encodeWithSignature("transfer(address,uint256)", msg.sender, amount)); OLD. Why always msg.sender? Should be strats[i].addr -> changed with strats[i].addr
def encode_function_data(initializer=None, *args):
    """Encodes the function call so we can work with an initializer.

    Args:
        initializer ([brownie.network.contract.ContractTx], optional):
        The initializer function we want to call. Example: `box.store`.
        Defaults to None.

        args (Any, optional):
        The arguments to pass to the initializer function

    Returns:
        [bytes]: Return the encoded bytes.
    """
    if not len(args): args = b''

    if initializer: return initializer.encode_input(*args)

    return b''


@pytest.fixture
def gov(accounts):
    yield accounts[0]

@pytest.fixture
def user(accounts):
    yield accounts[2]
    
@pytest.fixture
def rewards(accounts):
    yield accounts[1]

@pytest.fixture
def usdc_whale(accounts):
    acc = accounts.at("0x95bf7E307BC1ab0BA38ae10fc27084bC36FcD605", force=True) # 
    yield acc

@pytest.fixture
def usdc(interface):
    yield interface.IERC20Extended("0x04068DA6C83AFCFA0e13ba15A6696662335D5B75")

@pytest.fixture
def usdc_amount(usdc, usdc_whale, user):
    amount = 10_000 * 10 ** usdc.decimals()

    usdc.transfer(user, amount, {"from":usdc_whale})

    yield amount

@pytest.fixture
def LenderStrategy(LenderStrategy):
    yield LenderStrategy

@pytest.fixture
def vault(pm, gov, usdc):
    Vault = pm(config["dependencies"][1]).Vault
    vault = gov.deploy(Vault)
    vault.initialize(usdc, gov, gov, "TestVault", "testUSDC", gov)
    vault.setDepositLimit(2 ** 256 - 1, {"from": gov})
    vault.setManagement(gov, {"from": gov})
    yield vault

@pytest.fixture
def strategy(
    gov,
    LenderStrategy,
    vault,
    multistrat_proxy,
    husdc_gauge,
    husdc
):
    strategy = gov.deploy(LenderStrategy, vault, "Lender", multistrat_proxy.address, husdc_gauge, husdc.address)
    strategy.setKeeper(gov)

    vault.addStrategy(strategy, 10_000, 0, 2 ** 256 - 1, 1_000, {"from": gov})
    yield strategy


@pytest.fixture
def deployed_vault(
    chain,
    usdc,
    vault,
    user,
    usdc_amount
):
    # Deposit to the vault
    usdc.approve(vault.address, usdc_amount, {"from": user})
    print("Amount: ", usdc_amount)
    print("User: ", user)
    # harvest
    chain.sleep(1)

    print("Vault: ", usdc.balanceOf(vault.address))
    print("Strategy: ", usdc.balanceOf(usdc.address))
    yield vault

@pytest.fixture
def husdc_whale(accounts):
    acc = accounts.at("0x154001A2F9f816389b2F6D9E07563cE0359D813D", force=True) # 
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
def minter(Minter):
    yield Minter.at("0x42B458056f887Fd665ed6f160A59Afe932e1F559")
@pytest.fixture
def proxy(veHNDVoter, gov, oz):
    implementation = veHNDVoter.deploy({"from": gov})
    proxy_admin = oz.ProxyAdmin.deploy({"from": gov})
    box_encoded_initializer_function = encode_function_data(implementation.initialize, gov.address)
    proxy = oz.TransparentUpgradeableProxy.deploy(
        implementation,
        proxy_admin,
        box_encoded_initializer_function,
        {"from": gov},
    )
    
    proxy_voter = Contract.from_abi("veHNDVoter", proxy, veHNDVoter.abi)
    yield proxy_voter

@pytest.fixture
def multistrat_proxy(gov, proxy, MultiStrategyProxy):
    multistrategy = MultiStrategyProxy.deploy({"from": gov})
    multistrategy.initialize(gov, proxy)
    proxy.setStrategy(multistrategy.address, {"from": gov})
    yield multistrategy

@pytest.fixture
def husdc_gauge():
    yield "0x818b3dff96d01590Caf72965e6F50b24331EfdEC"

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
