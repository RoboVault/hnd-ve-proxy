import pytest
from brownie import config, accounts, Contract


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
def comptroller(interface):
    yield interface.ComptrollerInterface("0x21A4961B11c940fbeF57b1EB64FD646c880377e4")

@pytest.fixture
def user(accounts):
    yield accounts[2]
    
@pytest.fixture
def user2(accounts):
    yield accounts[3]
    
@pytest.fixture
def rewards(accounts):
    yield accounts[1]

@pytest.fixture
def usdc_whale(accounts):
    acc = accounts.at("0x95bf7E307BC1ab0BA38ae10fc27084bC36FcD605", force=True) # 
    yield acc

@pytest.fixture
def frax_whale(accounts):
    acc = accounts.at("0x7a656B342E14F745e2B164890E88017e27AE7320", force=True) # 
    yield acc

@pytest.fixture
def usdc(interface):
    yield interface.IERC20Extended("0x04068DA6C83AFCFA0e13ba15A6696662335D5B75")

@pytest.fixture
def frax(interface):
    yield interface.IERC20Extended("0xdc301622e621166BD8E82f2cA0A26c13Ad0BE355")

@pytest.fixture
def usdc_amount(usdc, usdc_whale, user):
    amount = 10_000 * 10 ** usdc.decimals()
    usdc.transfer(user, amount, {"from":usdc_whale})
    yield amount

@pytest.fixture
def frax_amount(frax, frax_whale, user):
    amount = 10_000 * 10 ** frax.decimals()
    yield amount


# @pytest.fixture
# def husdc_whale(user, accounts, comtroller):
    
#     acc = accounts.at("0x154001A2F9f816389b2F6D9E07563cE0359D813D", force=True) # 
#     yield acc

@pytest.fixture
def husdc(interface):
    yield interface.CTokenI("0x243E33aa7f6787154a8E59d3C27a66db3F8818ee")

@pytest.fixture
def hfrax(interface):
    yield interface.CTokenI("0xb4300e088a3AE4e624EE5C71Bc1822F68BB5f2bc")

@pytest.fixture
def hnd(interface):
    yield interface.IERC20Extended("0x10010078a54396F62c96dF8532dc2B4847d47ED3")



@pytest.fixture
def minter(Minter):
    yield Minter.at("0x2105dE165eD364919703186905B9BB5B8015F13c")
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
    yield "0x7BFE7b45c8019DEDc66c695Ac70b8fc2c0421584"

@pytest.fixture
def oz(pm):
    yield pm(config["dependencies"][0])


# Function scoped isolation fixture to enable xdist.
# Snapshots the chain before each test and reverts after test completion.
@pytest.fixture(scope="function", autouse=True)
def shared_setup(fn_isolation):
    pass
